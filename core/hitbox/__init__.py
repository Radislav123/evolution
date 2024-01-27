from typing import Optional

import arcade


class CustomHitBoxAlgorithm(arcade.hitbox.PymunkHitBoxAlgorithm):
    def __init__(self, *, detail: Optional[float] = None) -> None:
        super().__init__(detail = detail or self.default_detail)
        self._cache_name += f"|custom"
