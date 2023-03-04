import base64
import hashlib
import hmac
import json
import time
from typing import Optional

import requests

from ....common.utils import SIDE_MAPPING, flat_uuid
from ..exceptions import KucoinAPIException, KucoinRequestException
from ..validations import (validate_amount_size, validate_hidden_and_iceberg,
                           validate_iceberg, validate_post_only, validate_side,
                           validate_stop, validate_stop_loss_take_profit,
                           validate_time_in_force)


class Client:
    API_URL = "https://api-futures.kucoin.com"
    API_V1 = "v1"

    DEFAULT_HEADERS = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    def __init__(self, api_key, api_secret, passphrase):
        """Kucoin API Client constructor

        https://docs.kucoin.com/

        :param api_key: Api Token Id
        :type api_key: string
        :param api_secret: Api Secret
        :type api_secret: string
        :param passphrase: Api Passphrase used to create API
        :type passphrase: string
        """
        self.API_KEY = api_key
        self.API_SECRET = api_secret
        self.API_PASSPHRASE = passphrase

    @staticmethod
    def _handle_response(response):
        """Internal helper for handling API responses from the Kucoin server.
        Raises the appropriate exceptions when necessary; otherwise, returns 
        the response.
        """

        if not str(response.status_code).startswith('2'):
            raise KucoinAPIException(response)
        try:
            res = response.json()

            if 'code' in res and res['code'] != "200000":
                raise KucoinAPIException(response)

            if 'success' in res and not res['success']:
                raise KucoinAPIException(response)

            # by default return full response
            # if it's a normal response we have a data attribute, return that
            if 'data' in res:
                res = res['data']
            return res
        except ValueError:
            raise KucoinRequestException(f'Invalid Response: {response.text}')

    def _create_path(self, path, api_version=None):
        api_version = api_version or self.API_V1
        return f'/api/{api_version}/{path}'

    def _create_url(self, path):
        return f'{self.API_URL}{path}'

    def _generate_signature(
        self,
        nonce: str,
        method: str,
        api_path: str,
        data: str
    ) -> bytes:
        str_to_sign = f"{nonce}{method}{api_path}{data}"
        signature = base64.b64encode(
            hmac.new(
                self.API_SECRET.encode('utf-8'),
                str_to_sign.encode('utf-8'),
                hashlib.sha256
            ).digest()
        )
        return signature

    def _generate_passphrase(self) -> bytes:
        return base64.b64encode(
            hmac.new(
                self.API_SECRET.encode('utf-8'),
                self.API_PASSPHRASE.encode('utf-8'),
                hashlib.sha256
            ).digest()
        )

    def _request(
            self,
            method: str,
            path: str,
            api_version: Optional[str] = None,
            **kwargs
    ) -> dict:
        # set default requests timeout
        data = kwargs.get('data', {})
        headers = kwargs.get('headers', self.DEFAULT_HEADERS)

        data = json.dumps(data)

        full_path = self._create_path(path, api_version)
        url = self._create_url(full_path)

        # generate signature
        nonce = int(time.time() * 1000)
        headers['KC-API-TIMESTAMP'] = str(nonce)
        headers['KC-API-SIGN'] = self._generate_signature(
            nonce, method, full_path, data)
        headers['KC-API-KEY'] = self.API_KEY
        headers['KC-API-PASSPHRASE'] = self._generate_passphrase()
        headers['KC-API-KEY-VERSION'] = "2"

        response = requests.request(
            method=method,
            url=url,
            data=data,
            headers=headers
        )
        return self._handle_response(response)

    def _create_order(
        self,
        order: dict,
        amount: float,
        stop_loss_price: float,
        take_profit_price: float
    ) -> dict:
        validate_side(order["side"])
        validate_stop(
            order.get("stop"),
            order.get("stopPrice"),
            order.get("stopPriceType")
        )
        validate_stop_loss_take_profit(
            order.get("stop"),
            stop_loss_price,
            take_profit_price)
        validate_amount_size(amount, order.get("size"))

        if order.get("clientOid") is None:
            order["clientOid"] = flat_uuid()

        if amount:
            symbol_info = self.contract_info(order['symbol'])
            multiplier = symbol_info.get("multiplier")
            size = None
            if amount >= 1 and multiplier < 1:
                size = int(amount * (1 / multiplier))
            else:
                size = amount // multiplier

            if size is None:
                raise
            order["size"] = size

        new_order_response = self._request("POST", "orders", data=order)

        if stop_loss_price:
            stop_loss_order = order.copy()
            stop_loss_order["clientOid"] = flat_uuid()
            stop_loss_order["side"] = SIDE_MAPPING.get(order['side'])
            stop_loss_order["stop"] = "down" if order['side'] == "buy" else "up"
            stop_loss_order["stopPrice"] = stop_loss_price
            stop_loss_order["stopPriceType"] = "TP"
            stop_loss_order["reduceOnly"] = True
            self._request("POST", "orders", data=stop_loss_order)

        if take_profit_price:
            take_profit_order = order.copy()
            take_profit_order["clientOid"] = flat_uuid()
            take_profit_order["side"] = SIDE_MAPPING[order['side']]
            take_profit_order["stop"] = "up" if order['side'] == "buy" else "down"
            take_profit_order["stopPrice"] = take_profit_price
            take_profit_order["stopPriceType"] = "TP"
            take_profit_order["reduceOnly"] = True
            self._request("POST", "orders", data=take_profit_order)

        return new_order_response

    def contract_info(self, symbol: str) -> dict:
        return self._request("GET", f"contracts/{symbol}")

    def create_limit_order(
        self,
        side: str,
        price: str,
        symbol: str,
        leverage: str,
        amount: Optional[float] = None,
        size: Optional[int] = None,
        client_oid: Optional[bool] = None,
        remark: Optional[str] = None,
        stop: Optional[str] = None,
        stop_price: Optional[str] = None,
        stop_price_type: Optional[str] = None,
        reduce_only: Optional[str] = None,
        close_order: Optional[str] = None,
        force_hold: Optional[bool] = None,
        time_in_force: Optional[str] = None,
        post_only: Optional[str] = None,
        hidden: Optional[str] = None,
        iceberg: Optional[str] = None,
        visible_size: Optional[str] = "",
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
    ) -> dict:
        # Validate input
        validate_time_in_force(time_in_force)
        validate_post_only(post_only, time_in_force)
        validate_hidden_and_iceberg(hidden, iceberg)
        validate_iceberg(iceberg, visible_size)

        order = {
            'symbol': symbol.upper(),
            'side': side.lower(),
            'type': "limit",
            'price': price,
            'size': size
        }

        if client_oid:
            order['clientOid'] = client_oid
        if leverage:
            order['leverage'] = leverage
        if remark:
            order['remark'] = remark
        if stop:
            order['stop'] = stop
        if stop_price:
            order['stopPrice'] = stop_price
        if stop_price_type:
            order['stopPriceType'] = stop_price_type
        if reduce_only:
            order['reduceOnly'] = reduce_only
        if close_order:
            order['closeOrder'] = close_order
        if force_hold:
            order['forceHold'] = force_hold
        if hidden:
            order['hidden'] = hidden
        if iceberg:
            order['iceberg'] = iceberg
            order['visible_size'] = visible_size

        return self._create_order(
            order,
            amount,
            stop_loss_price,
            take_profit_price
        )

    def create_market_order(
        self,
        side: str,
        symbol: str,
        leverage: str,
        amount: Optional[float] = None,
        size: Optional[int] = None,
        client_oid: Optional[bool] = None,
        remark: Optional[str] = None,
        stop: Optional[str] = None,
        stop_price: Optional[str] = None,
        stop_price_type: Optional[str] = None,
        reduce_only: Optional[str] = None,
        close_order: Optional[str] = None,
        force_hold: Optional[bool] = None,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
    ) -> dict:

        order = {
            'symbol': symbol.upper(),
            'side': side.lower(),
            'type': "market",
            'size': size
        }

        if client_oid:
            order['clientOid'] = client_oid
        if leverage:
            order['leverage'] = leverage
        if remark:
            order['remark'] = remark
        if stop:
            order['stop'] = stop
        if stop_price:
            order['stopPrice'] = stop_price
        if stop_price_type:
            order['stopPriceType'] = stop_price_type
        if reduce_only:
            order['reduceOnly'] = reduce_only
        if close_order:
            order['closeOrder'] = close_order
        if force_hold:
            order['forceHold'] = force_hold

        return self._create_order(
            order,
            amount,
            stop_loss_price,
            take_profit_price
        )
