use altrepo_rdb_client::AltrepoClient;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = AltrepoClient::new()?;

    let ping = client.ping().await?;
    println!("Ping response: {}", ping.message);

    let version = client.version().await?;
    println!("{} {}", version.name, version.version);

    Ok(())
}
