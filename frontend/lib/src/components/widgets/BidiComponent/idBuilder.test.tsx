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

/* eslint import/no-unresolved: off, import/extensions: off */
/**
 * Tests for the makeTriggerId helper. These are written before the actual
 * implementation – they will fail until `../idBuilder.ts` provides the helper.
 */

import { describe, expect, it } from "vitest"

import { makeTriggerId } from "./idBuilder"

describe("makeTriggerId", () => {
  it("concatenates base and event with the expected delimiter", () => {
    expect(makeTriggerId("myComponent", "click")).toBe("myComponent__click")
    expect(makeTriggerId("myComponent", "change")).toBe("myComponent__change")
    expect(makeTriggerId("myComponent", "input")).toBe("myComponent__input")
    expect(makeTriggerId("myComponent", "submit")).toBe("myComponent__submit")
    expect(makeTriggerId("myComponent", "reset")).toBe("myComponent__reset")
    expect(makeTriggerId("myComponent", "blur")).toBe("myComponent__blur")
    expect(makeTriggerId("myComponent", "focus")).toBe("myComponent__focus")
  })

  it("throws when base or event contains the delimiter", () => {
    expect(() => makeTriggerId("bad__base", "click")).toThrow()
    expect(() => makeTriggerId("base", "bad__event")).toThrow()
  })
})
