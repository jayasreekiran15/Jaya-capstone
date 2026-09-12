1. In one sentence: what's lost if the process restarts? (i.e., what is the `request_counts` dict missing that a real metrics system would provide?)

 A.  All the counts go zero except health that counts 1.

2. In one sentence: under heavy concurrency, would two simultaneous requests to `/    health` always result in the counter going from N to N+2? Why or why not?

A.  Under heavy concurrency request to '/health' always result 1.