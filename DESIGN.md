System Disgn
============

Below shows how `damo` works with DAMON/DAMOS in kernel.

                       ┌──────┐
           ┌───────────┤ DAMO │
           │Read       └──┬───┘
           ▼              │read/write
      ┌──────────┐        ▼
      │Monitoring│   ┌─────────┐       User space
    ──┤  result  ├───┤  sysfs  ├─────────────────
      │   file   │   └─┬─────┬─┘     Kernel space
      └──────────┘     │     │Operation scheme
           ▲           │     ▼
           │    Monitor│  ┌──────────────┐
           │    request│  │     DAMOS    │
           │           │  └────────────┬─┘
           │           │   ▲ Monitor   │
           │           │   │ request/  │
           │           ▼   ▼ response  │Control
           │Write┌────────────┐        │swap,
           └─────┤   DAMON    │        │LRU,
                 └──────┬─────┘        │THP
                        │Check access  │
                        ▼              ▼
                 ┌───────────────────────┐
                 │         Memory        │
                 └───────────────────────┘
