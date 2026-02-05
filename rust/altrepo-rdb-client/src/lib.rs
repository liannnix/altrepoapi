//! `altrepo-rdb-client` — асинхронный Rust-клиент для REST API `rdb.altlinux.org`.
//!
//! Базовые возможности:
//! - проверка доступности API (`/api/ping`)
//! - чтение версии API (`/api/version`)
//! - универсальные GET-запросы к любым endpoint'ам с query-параметрами

mod models;

pub use models::{ApiVersion, PingResponse};

use reqwest::header::{HeaderMap, HeaderValue, AUTHORIZATION};
use reqwest::StatusCode;
use serde::de::DeserializeOwned;
use std::fmt::Display;
use thiserror::Error;
use url::Url;

const DEFAULT_BASE_URL: &str = "https://rdb.altlinux.org";

#[derive(Debug, Clone)]
pub struct AltrepoClient {
    base_url: Url,
    http: reqwest::Client,
}

#[derive(Debug, Error)]
pub enum AltrepoError {
    #[error("invalid base url: {0}")]
    InvalidBaseUrl(#[from] url::ParseError),

    #[error("http transport error: {0}")]
    Transport(#[from] reqwest::Error),

    #[error("http status error: {status} ({body})")]
    HttpStatus { status: StatusCode, body: String },

    #[error("failed to build auth header: {0}")]
    InvalidHeader(#[from] reqwest::header::InvalidHeaderValue),
}

impl AltrepoClient {
    pub fn new() -> Result<Self, AltrepoError> {
        Self::with_base_url(DEFAULT_BASE_URL)
    }

    pub fn with_base_url(base_url: &str) -> Result<Self, AltrepoError> {
        let url = Url::parse(base_url)?;
        Ok(Self {
            base_url: url,
            http: reqwest::Client::new(),
        })
    }

    pub fn with_bearer_token(mut self, token: impl AsRef<str>) -> Result<Self, AltrepoError> {
        let mut headers = HeaderMap::new();
        let value = format!("Bearer {}", token.as_ref());
        headers.insert(AUTHORIZATION, HeaderValue::from_str(&value)?);

        self.http = reqwest::Client::builder()
            .default_headers(headers)
            .build()?;

        Ok(self)
    }

    pub fn base_url(&self) -> &Url {
        &self.base_url
    }

    pub async fn ping(&self) -> Result<PingResponse, AltrepoError> {
        self.get_json("/api/ping", None::<Vec<(String, String)>>)
            .await
    }

    pub async fn version(&self) -> Result<ApiVersion, AltrepoError> {
        self.get_json("/api/version", None::<Vec<(String, String)>>)
            .await
    }

    pub async fn get_json<T, K, V>(
        &self,
        path: &str,
        query: Option<Vec<(K, V)>>,
    ) -> Result<T, AltrepoError>
    where
        T: DeserializeOwned,
        K: Display,
        V: Display,
    {
        let mut url = self.base_url.join(path.trim_start_matches('/'))?;

        if let Some(query) = query {
            let mut pairs = url.query_pairs_mut();
            for (k, v) in query {
                pairs.append_pair(&k.to_string(), &v.to_string());
            }
        }

        let response = self.http.get(url).send().await?;
        let status = response.status();

        if status.is_success() {
            Ok(response.json::<T>().await?)
        } else {
            let body = response.text().await.unwrap_or_else(|_| String::new());
            Err(AltrepoError::HttpStatus { status, body })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builds_default_client() {
        let client = AltrepoClient::new().expect("client should be created");
        assert_eq!(client.base_url().as_str(), "https://rdb.altlinux.org/");
    }

    #[test]
    fn joins_url_path_safely() {
        let client = AltrepoClient::with_base_url("https://rdb.altlinux.org")
            .expect("client should be created");
        let url = client
            .base_url
            .join("api/ping")
            .expect("url should be valid");
        assert_eq!(url.as_str(), "https://rdb.altlinux.org/api/ping");
    }
}
