from typing import Optional

import requests

from .exceptions import OrderParameterValidationException

VALID_SIDE = ("buy", "sell")
VALID_STOP = ("down", "up")
VALID_STOP_PRICE_TYPE = ("TP", "MP", "IP")
VALID_TIME_IN_FORCE = ("GTC", "IOC")


def validate_side(side: str) -> None:
    if side not in VALID_SIDE:
        raise OrderParameterValidationException(
            f"Order 'side' need to be one of {VALID_SIDE}"
        )


def validate_stop(
    stop: Optional[str],
    stop_price: Optional[str],
    stop_price_type: Optional[str]
) -> None:
    if not stop:
        return

    if stop not in VALID_STOP:
        raise OrderParameterValidationException(
            f"Property 'stop' need to be one of {VALID_STOP}"
        )
    if stop_price_type not in VALID_STOP_PRICE_TYPE:
        raise OrderParameterValidationException(
            "Property 'stop_price_type' need to be "
            f"one of {VALID_STOP_PRICE_TYPE}"
        )
    if not stop_price:
        raise OrderParameterValidationException(
            f"Property 'stop_price' need to be defined"
        )


def validate_stop_loss_take_profit(
    stop: Optional[str],
    stop_loss: Optional[str],
    take_profit: Optional[str]
) -> None:
    if stop and (stop_loss or take_profit):
        raise OrderParameterValidationException(
            f"If property 'stop_loss' or 'take_profit' defined "
            "proerty 'stop' need to be empty"
        )


def validate_time_in_force(time_in_force: Optional[str]) -> None:
    if not time_in_force:
        return

    if time_in_force not in VALID_TIME_IN_FORCE:
        raise OrderParameterValidationException(
            "Property 'time_in_force' need to be "
            f"one of: {VALID_TIME_IN_FORCE}"
        )


def validate_post_only(
        time_in_force: Optional[str],
        post_only: Optional[bool]
) -> None:
    if post_only and time_in_force != VALID_TIME_IN_FORCE[0]:
        raise OrderParameterValidationException(
            "If property 'post_only' defined, "
            f"'time_in_force' need to be {VALID_TIME_IN_FORCE[0]}"
        )


def validate_hidden_and_iceberg(
    hidden: Optional[bool],
    iceberg: Optional[bool]
) -> None:
    if hidden and iceberg:
        raise OrderParameterValidationException(
            f"Only one of 'hodden' and 'iceberg' can be defined"
        )


def validate_iceberg(
    iceberg: Optional[bool],
    visible_size: Optional[int]
) -> None:
    if iceberg and not visible_size:
        raise OrderParameterValidationException(
            f"If property 'iceberg' is defined, proerty 'visible_size' need to be empty"
        )


def validate_amount_size(
    amount: Optional[float],
    size: Optional[int]
) -> None:
    if amount and size:
        raise OrderParameterValidationException(
            f"Either 'amount' or 'size' need to be empty."
        )
