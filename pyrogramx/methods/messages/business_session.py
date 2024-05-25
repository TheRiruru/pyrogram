#  Pyrogram - Telegram MTProto API Client Library for Python
#  Copyright (C) 2017-present Dan <https://github.com/delivrance>
#
#  This file is part of Pyrogram.
#
#  Pyrogram is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Pyrogram is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with Pyrogram.  If not, see <http://www.gnu.org/licenses/>.

import pyrogramx
from pyrogramx import raw
from pyrogramx.errors import AuthBytesInvalid
from pyrogramx.session import Session
from pyrogramx.session.auth import Auth


async def get_session(client: "pyrogramx.Client", business_connection_id: str) -> Session:
    dc_id = client.business_connections.get(business_connection_id)

    if dc_id is None:
        connection = await client.session.invoke(
            raw.functions.account.GetBotBusinessConnection(
                connection_id=business_connection_id
            )
        )

        dc_id = client.business_connections[business_connection_id] = connection.updates[0].connection.dc_id

    if dc_id == await client.storage.dc_id():
        return client.session

    async with client.sessions_lock:
        if client.sessions.get(dc_id):
            return client.sessions[dc_id]

        session = client.sessions[dc_id] = Session(
            client, dc_id,
            await Auth(client, dc_id, await client.storage.test_mode()).create(),
            await client.storage.test_mode()
        )

        await session.start()

        for _ in range(3):
            exported_auth = await client.invoke(
                raw.functions.auth.ExportAuthorization(
                    dc_id=dc_id
                )
            )

            try:
                await session.invoke(
                    raw.functions.auth.ImportAuthorization(
                        id=exported_auth.id,
                        bytes=exported_auth.bytes
                    )
                )
            except AuthBytesInvalid:
                continue
            else:
                break
        else:
            await session.stop()
            raise AuthBytesInvalid

        return session
