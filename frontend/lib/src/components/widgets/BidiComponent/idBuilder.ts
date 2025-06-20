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

/*
 * Helper utilities for constructing widget ids for per-event trigger values.
 *
 * The identifier follows the pattern: `${base}${EVENT_DELIM}${event}` where
 * `EVENT_DELIM` is a shared constant (double underscore) that guarantees we
 * can later split the id back into its parts loss-lessly.
 */

import { EVENT_DELIM } from "./constants"

/**
 * Build the trigger widget id given a component's base id and an event name.
 *
 * @throws {Error} If either argument already contains the delimiter. This
 *                 prevents ambiguous ids that would break round-trip parsing.
 */
export function makeTriggerId(base: string, event: string): string {
  if (base.includes(EVENT_DELIM)) {
    throw new Error(
      "Base component id must not contain the delimiter sequence"
    )
  }
  if (event.includes(EVENT_DELIM)) {
    throw new Error("Event name must not contain the delimiter sequence")
  }

  return `${base}${EVENT_DELIM}${event}`
}
