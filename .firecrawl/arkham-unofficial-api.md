Explore

## Unofficial Arkham API - OpenAPI 3.0  ```  1.0.0  ```    ``` OAS 3.0 ```

[arkham.yaml](https://cipher-rc5.github.io/UnofficialArkhamAPI/arkham.yaml)

This is an unofficial version of the Arkham Intelligence API based on the OpenAPI 3.0 specification.
Please download and use on your own local clients; it is not advisable to load any private API-Keys into non-local systems.

Some useful links:

- [Arkham API Documentation](https://arkham-intelligence.notion.site/arkham-intelligence/Arkham-API-Access-9232652274854efaa8a67633a94a2595)

Contact:

- [Made by Cipher](https://twitter.com/Cipher0091)

[Apache 2.0](http://www.apache.org/licenses/LICENSE-2.0.html)

[Find out more about Arkham Intelligence](http://arkhamintelligence.com/)

Servers

https://api.arkhamintelligence.com

Authorize

### [Transfers](https://cipher-rc5.github.io/UnofficialArkhamAPI/\#/Transfers)    Operations about transfers

GET
[/transfers](https://cipher-rc5.github.io/UnofficialArkhamAPI/#/Transfers/get_transfers)

Get transfers

### [Intelligence](https://cipher-rc5.github.io/UnofficialArkhamAPI/\#/Intelligence)    Detailed insights about addresses

GET
[/intelligence/address/{address}](https://cipher-rc5.github.io/UnofficialArkhamAPI/#/Intelligence/get_intelligence_address__address_)

Get intelligence about an address

GET
[/intelligence/address/{address}/all](https://cipher-rc5.github.io/UnofficialArkhamAPI/#/Intelligence/get_intelligence_address__address__all)

Get all intelligence about an address

### [History](https://cipher-rc5.github.io/UnofficialArkhamAPI/\#/History)    Historical data for entities and addresses

GET
[/history/entity/{entity}](https://cipher-rc5.github.io/UnofficialArkhamAPI/#/History/get_history_entity__entity_)

Get all history about an address

GET
[/history/address/{address}](https://cipher-rc5.github.io/UnofficialArkhamAPI/#/History/get_history_address__address_)

Get all history about an address

### [Portfolio](https://cipher-rc5.github.io/UnofficialArkhamAPI/\#/Portfolio)    Portfolio data for entities and addresses

GET
[/portfolio/entity/{entity}](https://cipher-rc5.github.io/UnofficialArkhamAPI/#/Portfolio/get_portfolio_entity__entity_)

Get portfolio data about a specific entity

GET
[/portfolio/address/{address}](https://cipher-rc5.github.io/UnofficialArkhamAPI/#/Portfolio/get_portfolio_address__address_)

Get portfolio data about a specific address

### [Token](https://cipher-rc5.github.io/UnofficialArkhamAPI/\#/Token)    Information about token holders

GET
[/token/holders/{pricing\_id}](https://cipher-rc5.github.io/UnofficialArkhamAPI/#/Token/get_token_holders__pricing_id_)

Get all token holders for a specific CoinGecko pricing id

### [default](https://cipher-rc5.github.io/UnofficialArkhamAPI/\#/default)

GET
[/transfers/histogram](https://cipher-rc5.github.io/UnofficialArkhamAPI/#/default/get_transfers_histogram)

Get transfers histogram

GET
[/token/holders/{chain}/{address}](https://cipher-rc5.github.io/UnofficialArkhamAPI/#/default/get_token_holders__chain___address_)

Get all history about an address