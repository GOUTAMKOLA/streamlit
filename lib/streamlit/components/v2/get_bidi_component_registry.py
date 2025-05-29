# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022-2025)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from streamlit.components.v2.component_registry import BidiComponentRegistry


def get_bidi_component_registry() -> BidiComponentRegistry:
    """Returns the singleton BidiComponentRegistry instance.

    Returns
    -------
    BidiComponentRegistry
        The singleton BidiComponentRegistry instance.
    """
    from streamlit.components.v2.component_registry import BidiComponentRegistry
    from streamlit.runtime import Runtime

    if Runtime.exists():
        return Runtime.instance().bidi_component_registry

    # Return a local registry when running without the streamlit runtime
    return BidiComponentRegistry()
