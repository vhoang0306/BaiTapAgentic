| Pattern | Scenario | Correct | Avg model calls | Avg tokens | Avg tool calls | Blocked | Unsafe pay | Errors |
|---|---|---|---|---|---|---|---|---|
| ReAct | success | 3/3 | 4.0 | 6009 | 3.0 | 0 | 0 | 0 |
| ReAct | no_valid | 3/3 | 2.0 | 2905 | 1.0 | 0 | 0 | 0 |
| ReAct | sold_out | 3/3 | 5.3 | 8527 | 4.3 | 0 | 0 | 0 |
| ReAct | transient | 3/3 | 5.3 | 8292 | 4.3 | 0 | 0 | 0 |
| Plan-then-Execute | success | 3/3 | 1.0 | 1598 | 4.0 | 0 | 0 | 0 |
| Plan-then-Execute | no_valid | 3/3 | 1.0 | 1331 | 1.0 | 0 | 0 | 0 |
| Plan-then-Execute | sold_out | 0/3 | 1.0 | 1898 | 2.0 | 0 | 0 | 0 |
| Plan-then-Execute | transient | 0/3 | 1.0 | 1544 | 2.0 | 0 | 0 | 0 |
| Hybrid | success | 3/3 | 1.0 | 1454 | 4.0 | 0 | 0 | 0 |
| Hybrid | no_valid | 3/3 | 1.0 | 1279 | 1.0 | 0 | 0 | 0 |
| Hybrid | sold_out | 3/3 | 4.0 | 6840 | 4.0 | 0 | 0 | 0 |
| Hybrid | transient | 3/3 | 4.0 | 6430 | 4.0 | 0 | 0 | 0 |

| Pattern | Correct | Avg model calls | Avg tokens | Avg tool calls | Unsafe pay |
|---|---|---|---|---|---|
| ReAct | 12/12 | 4.17 | 6433 | 3.17 | 0 |
| Plan-then-Execute | 6/12 | 1.00 | 1593 | 2.25 | 0 |
| Hybrid | 12/12 | 2.50 | 4001 | 3.25 | 0 |
