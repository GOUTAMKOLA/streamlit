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

import { describe, expect, it } from "vitest"
import { renderHook } from "@testing-library/react"

import { useStableArray } from "./useStableArray"

describe("#useStableArray", () => {
  describe("basic functionality", () => {
    it.each([
      ["numbers", [1, 2, 3]],
      ["single element", [42]],
      ["strings", ["a", "b", "c"]],
      ["empty array", []],
      ["mixed types", [1, "a", true, null]],
    ])("should return a stable array for %s", (_, array) => {
      const { result } = renderHook(() => useStableArray(array))
      expect(result.current).toEqual(array)
      expect(Array.isArray(result.current)).toBe(true)
    })

    it("should handle objects", () => {
      const array = [{ id: 1 }, { id: 2 }]
      const { result } = renderHook(() => useStableArray(array))
      expect(result.current).toEqual(array)
      expect(Array.isArray(result.current)).toBe(true)
    })

    it("should handle nested arrays", () => {
      const array = [
        [1, 2],
        [3, 4],
      ]
      const { result } = renderHook(() => useStableArray(array))
      expect(result.current).toEqual(array)
      expect(Array.isArray(result.current)).toBe(true)
    })
  })

  describe("referential stability", () => {
    it("should return the same reference when called multiple times with same array", () => {
      const array = [1, 2, 3]
      const { result, rerender } = renderHook(() => useStableArray(array))

      const firstResult = result.current
      rerender()
      const secondResult = result.current

      expect(firstResult).toBe(secondResult)
    })

    it("should return different references for different array contents", () => {
      const array1 = [1, 2, 3]
      const array2 = [1, 2, 4] // Different content

      const { result: result1 } = renderHook(() => useStableArray(array1))
      const { result: result2 } = renderHook(() => useStableArray(array2))

      expect(result1.current).not.toBe(result2.current)
    })
  })

  describe("array updates", () => {
    it("should return new reference when array content changes", () => {
      const { result, rerender } = renderHook(
        ({ array }) => useStableArray(array),
        { initialProps: { array: [1, 2, 3] } }
      )

      const firstResult = result.current

      // Change the array content
      rerender({ array: [1, 2, 4] })

      const secondResult = result.current

      expect(firstResult).not.toBe(secondResult)
      expect(secondResult).toEqual([1, 2, 4])
    })

    it("should handle array length changes", () => {
      const { result, rerender } = renderHook(
        ({ array }) => useStableArray(array),
        { initialProps: { array: [1, 2, 3] } }
      )

      const firstResult = result.current

      // Add element
      rerender({ array: [1, 2, 3, 4] })

      const secondResult = result.current

      expect(firstResult).not.toBe(secondResult)
      expect(secondResult).toEqual([1, 2, 3, 4])

      // Remove element
      rerender({ array: [1, 2] })

      const thirdResult = result.current

      expect(secondResult).not.toBe(thirdResult)
      expect(thirdResult).toEqual([1, 2])
    })
  })

  describe("edge cases", () => {
    it.each([
      ["array with commas in strings", ["a,b", "c,d"]],
      ["array with empty strings", ["", "test", ""]],
      ["array with special characters", ["@#$", "%^&", "()"]],
      ["array with numbers as strings", ["1", "2", "3"]],
    ])("should handle %s correctly", (_, array) => {
      const { result } = renderHook(() => useStableArray(array))
      expect(result.current).toEqual(array)
    })

    it("should handle array with boolean values", () => {
      const array = [true, false, true]
      const { result } = renderHook(() => useStableArray(array))
      expect(result.current).toEqual(array)
    })

    it("should handle array with null and undefined", () => {
      const array = [null, undefined, "value"]
      const { result } = renderHook(() => useStableArray(array))
      expect(result.current).toEqual(array)
    })

    it("should handle arrays with duplicate values", () => {
      const array = [1, 1, 2, 2, 3, 3]
      const { result } = renderHook(() => useStableArray(array))
      expect(result.current).toEqual(array)
    })
  })

  describe("memoization behavior", () => {
    it("should not mutate the original array", () => {
      const originalArray = [1, 2, 3]
      const { result } = renderHook(() => useStableArray(originalArray))

      // The returned array should be frozen, preventing mutations
      expect(() => {
        // @ts-expect-error - Testing runtime behavior of frozen array
        result.current.push(4)
      }).toThrow()

      // Original should remain unchanged
      expect(originalArray).toEqual([1, 2, 3])
      expect(result.current).toEqual([1, 2, 3])
    })

    it("should prevent mutations", () => {
      const array = [1, 2, 3]

      // First hook instance
      const { result: result1 } = renderHook(() => useStableArray(array))

      // Attempt to mutate should fail due to frozen array
      expect(() => {
        // @ts-expect-error - Testing runtime behavior of frozen array
        result1.current.push(4)
      }).toThrow()
    })

    it("should return same reference for arrays with same JSON representation", () => {
      const { result, rerender } = renderHook(
        ({ array }) => useStableArray(array),
        { initialProps: { array: [1, 2, 3] } }
      )

      const firstResult = result.current

      // Rerender with a new array instance but same content
      rerender({ array: [1, 2, 3] })

      const secondResult = result.current

      expect(firstResult).toBe(secondResult)
    })

    it("should be sensitive to array order", () => {
      const { result: result1 } = renderHook(() => useStableArray([1, 2, 3]))
      const { result: result2 } = renderHook(() => useStableArray([3, 2, 1]))

      expect(result1.current).not.toBe(result2.current)
      expect(result1.current).toEqual([1, 2, 3])
      expect(result2.current).toEqual([3, 2, 1])
    })
  })

  describe("JSON serialization edge cases", () => {
    it("should handle objects with different property order as different", () => {
      const obj1 = { a: 1, b: 2 }
      const obj2 = { b: 2, a: 1 }

      const { result: result1 } = renderHook(() => useStableArray([obj1]))
      const { result: result2 } = renderHook(() => useStableArray([obj2]))

      // JSON.stringify is sensitive to property order
      expect(result1.current).not.toBe(result2.current)
    })

    it("should handle arrays with functions (which JSON.stringify ignores)", () => {
      const func = (): void => {}
      const array = [1, func, 3]

      const { result } = renderHook(() => useStableArray(array))

      // The function should be preserved in the result even though JSON.stringify ignores it
      expect(result.current).toEqual([1, func, 3])
      expect(typeof result.current[1]).toBe("function")
    })

    it("should handle arrays with symbols (which JSON.stringify ignores)", () => {
      const sym = Symbol("test")
      const array = [1, sym, 3]

      const { result } = renderHook(() => useStableArray(array))

      // The symbol should be preserved in the result
      expect(result.current).toEqual([1, sym, 3])
      expect(typeof result.current[1]).toBe("symbol")
    })

    it("should handle arrays with undefined values", () => {
      const array = [1, undefined, 3]

      const { result } = renderHook(() => useStableArray(array))

      expect(result.current).toEqual([1, undefined, 3])
      expect(result.current[1]).toBeUndefined()
    })

    it("should handle arrays with Date objects", () => {
      const date1 = new Date("2023-01-01")
      const date2 = new Date("2023-01-01") // Same date, different instance

      const { result, rerender } = renderHook(
        ({ array }) => useStableArray(array),
        { initialProps: { array: [date1] } }
      )

      const firstResult = result.current

      // Rerender with equivalent date - should return same reference due to JSON serialization
      rerender({ array: [date2] })

      const secondResult = result.current

      expect(firstResult).toBe(secondResult)
      expect(secondResult[0]).toEqual(date1)
    })
  })

  describe("deep equality behavior", () => {
    it("should detect changes in nested objects", () => {
      const { result, rerender } = renderHook(
        ({ array }) => useStableArray(array),
        { initialProps: { array: [{ nested: { value: 1 } }] } }
      )

      const firstResult = result.current

      // Change nested value
      rerender({ array: [{ nested: { value: 2 } }] })

      const secondResult = result.current

      expect(firstResult).not.toBe(secondResult)
      expect(secondResult).toEqual([{ nested: { value: 2 } }])
    })

    it("should detect changes in nested arrays", () => {
      const { result, rerender } = renderHook(
        ({ array }) => useStableArray(array),
        {
          initialProps: {
            array: [
              [1, 2],
              [3, 4],
            ],
          },
        }
      )

      const firstResult = result.current

      // Change nested array
      rerender({
        array: [
          [1, 2],
          [3, 5],
        ],
      })

      const secondResult = result.current

      expect(firstResult).not.toBe(secondResult)
      expect(secondResult).toEqual([
        [1, 2],
        [3, 5],
      ])
    })
  })

  describe("performance characteristics", () => {
    it("should handle large arrays efficiently", () => {
      const largeArray = Array.from({ length: 1000 }, (_, i) => i)

      const { result } = renderHook(() => useStableArray(largeArray))

      expect(result.current).toEqual(largeArray)
      expect(result.current.length).toBe(1000)
    })

    it("should maintain referential stability across multiple rerenders with same large array", () => {
      const largeArray = Array.from({ length: 100 }, (_, i) => ({
        id: i,
        value: `item-${i}`,
      }))

      const { result, rerender } = renderHook(() => useStableArray(largeArray))

      const firstResult = result.current

      // Multiple rerenders with same array
      rerender()
      rerender()
      rerender()

      const finalResult = result.current

      expect(firstResult).toBe(finalResult)
    })
  })
})
