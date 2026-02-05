# altrepo-rdb-client

Асинхронная Rust-библиотека для работы с API `rdb.altlinux.org`.

## Возможности

- `AltrepoClient::new()` с базовым URL по умолчанию: `https://rdb.altlinux.org`
- методы:
  - `ping()` → `GET /api/ping`
  - `version()` → `GET /api/version`
- универсальный `get_json()` для произвольных GET endpoint'ов с query-параметрами
- поддержка Bearer-токена через `with_bearer_token()`

## Установка

```toml
[dependencies]
altrepo-rdb-client = { path = "./rust/altrepo-rdb-client" }
```

## Быстрый старт

```rust
use altrepo_rdb_client::AltrepoClient;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = AltrepoClient::new()?;

    let pong = client.ping().await?;
    println!("ping: {}", pong.message);

    let version = client.version().await?;
    println!("api version: {}", version.version);

    Ok(())
}
```
