# Request Flow

A typical web request enters the application service, performs business logic, and may call shared dependencies such as a relational database. Database work can therefore affect application latency and request success even when application process health remains normal.

Distributed traces should be used to identify which dependency span contributes most of the request duration. Correlating dependency spans with application metrics can distinguish application-side latency from downstream latency.
