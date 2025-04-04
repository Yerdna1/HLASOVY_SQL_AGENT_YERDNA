"""API pre komunikáciu s WebSocket serverom v reálnom čase."""

import os
import asyncio
import json
import uuid
import websockets
from datetime import datetime
import socket

# Import preložených častí
from .event_handler import SpracovatelUdalostiRealnehoCasu
from apka.widgets.spolocne import zapisovac

# Potrebné pre Azure, ponechané pre funkčnosť
socket.gethostbyname("localhost")


class APIRealnehoCasu(SpracovatelUdalostiRealnehoCasu):
    def __init__(
        self,
        url=None,
        api_kluc=None,
        api_verzia="2024-10-01-preview",
        nasadenie=None,
    ):
        super().__init__()
        self.pouzit_azure = os.getenv("USE_AZURE", "false").lower() == "true"

        if self.pouzit_azure:
            self.url = url or os.getenv("AZURE_OPENAI_URL")
            self.api_kluc = api_kluc or os.getenv("AZURE_OPENAI_API_KEY")
            self.api_verzia = api_verzia
            self.nasadenie = nasadenie or os.getenv("OPENAI_DEPLOYMENT_NAME_REALTIME", "gpt-4o-realtime-preview")
            self.user_agent = "ms-rtclient-0.4.3"
            self.id_poziadavky = uuid.uuid4()
        else:
            self.predvolena_url = "wss://api.openai.com/v1/realtime"
            self.url = url or self.predvolena_url
            self.api_kluc = api_kluc or os.getenv("OPENAI_API_KEY")

        self.ws = None

    def je_pripojeny(self):
        """Skontroluje, či je WebSocket spojenie aktívne."""
        return self.ws is not None

    def _zapis_log(self, *args):
        """Zaznamená správu do logu."""
        # Použijeme importovaný logger
        zapisovac.debug(f"[Websocket/{datetime.utcnow().isoformat()}]", *args)

    async def pripoj(self, model="gpt-4o-realtime-preview-2024-10-01"):
        """Nadviaže WebSocket spojenie."""
        if self.je_pripojeny():
            raise Exception("Už pripojené")

        if self.pouzit_azure:
            if not self.url:
                raise ValueError("Azure OpenAI URL je povinné")

            url_spojenia = f"wss://{self.url}/openai/realtime?api-version={self.api_verzia}&deployment={self.nasadenie}"
            # zapisovac.info(f"Pripája sa k Azure URL: {url_spojenia}")
            self.ws = await websockets.connect(
                url_spojenia,
                extra_headers={
                    "api-key": self.api_kluc,
                    "User-Agent": self.user_agent,
                    "x-ms-client-request-id": str(self.id_poziadavky),
                },
            )
        else:
            # zapisovac.info(f"Pripája sa k OpenAI URL: {self.url}")
            self.ws = await websockets.connect(
                f"{self.url}?model={model}",
                extra_headers={
                    "Authorization": f"Bearer {self.api_kluc}",
                    "OpenAI-Beta": "realtime=v1",
                },
            )

        self._zapis_log(f"Pripojené k {self.url}")
        # Spustenie úlohy na pozadí pre prijímanie správ
        asyncio.create_task(self._prijimaj_spravy())

    async def _prijimaj_spravy(self):
        """Prijíma správy z WebSocketu a odosiela ich spracovateľom."""
        try:
            async for sprava in self.ws:
                udalost = json.loads(sprava)
                if udalost.get("type") == "error":
                    zapisovac.error("CHYBA", udalost)
                self._zapis_log("prijaté:", udalost)
                # Odoslanie udalosti registrovaným spracovateľom
                self.odosli(f"server.{udalost['type']}", udalost)
                self.odosli("server.*", udalost)
        except websockets.exceptions.ConnectionClosedOK:
             self._zapis_log("Spojenie WebSocket bolo normálne uzavreté.")
        except websockets.exceptions.ConnectionClosedError as e:
             self._zapis_log(f"Spojenie WebSocket bolo neočakávane uzavreté: {e}")
        except Exception as e:
             self._zapis_log(f"Nastala chyba pri prijímaní správ: {e}")
        finally:
             # Zabezpečíme, že stav pripojenia je aktualizovaný
             self.ws = None
             self._zapis_log("Prijímanie správ ukončené.")


    async def posli(self, nazov_udalosti, data=None):
        """Odošle udalosť cez WebSocket."""
        if not self.je_pripojeny():
            raise Exception("APIRealnehoCasu nie je pripojené")
        data = data or {}
        if not isinstance(data, dict):
            raise Exception("dáta musia byť slovník (dictionary)")
        # Vytvorenie udalosti s ID
        udalost = {"event_id": self._generuj_id("evt_"), "type": nazov_udalosti, **data} # Kľúče 'event_id', 'type' sú súčasťou API
        # Odoslanie udalosti lokálnym spracovateľom
        self.odosli(f"client.{nazov_udalosti}", udalost)
        self.odosli("client.*", udalost)
        self._zapis_log("odoslané:", udalost)
        # Odoslanie udalosti cez WebSocket
        await self.ws.send(json.dumps(udalost))

    def _generuj_id(self, prefix):
        """Generuje unikátne ID s časovou značkou."""
        return f"{prefix}{int(datetime.utcnow().timestamp() * 1000)}"

    async def odpoj(self):
        """Uzavrie WebSocket spojenie."""
        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                 self._zapis_log(f"Chyba pri zatváraní WebSocketu: {e}")
            finally:
                ws_temp = self.ws # Uložíme referenciu pre logovanie
                self.ws = None
                self._zapis_log(f"Odpojené od {self.url}")
