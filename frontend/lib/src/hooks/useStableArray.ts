/**
 * Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022-2025)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { useMemo } from "react"

/**
 * This hook returns a stable array.
 *
 * @param array - The array to return a stable version of.
 * @returns A stable version of the array (frozen to prevent mutations).
 */
export const useStableArray = <T>(array: T[]): readonly T[] => {
  return useMemo(() => {
    return Object.freeze([...array])
    // These eslint rules are disabled because we want to use the stringified
    // version of the array as a cache key for the memoization.
    // eslint-disable-next-line react-hooks/react-compiler
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(array)])
}
