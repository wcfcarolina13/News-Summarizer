"""
The Grid API Integration - Query The Grid's Web3 metadata API.

The Grid provides standardized metadata about Web3 projects, products, and assets.
This module integrates with the CSV processor to:
1. Check if extracted news items match entities in The Grid
2. Provide TGS (The Grid Schema) data recommendations

API Endpoint: https://beta.node.thegrid.id/graphql
Docs: https://docs.thegrid.id/
"""

import re
import json
import requests
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from urllib.parse import quote


# =============================================================================
# CONFIGURATION
# =============================================================================

GRID_API_ENDPOINT = "https://beta.node.thegrid.id/graphql"

# Common crypto project name mappings (for better matching)
NAME_ALIASES = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "bnb": "binance",
    "xrp": "ripple",
    "ada": "cardano",
    "doge": "dogecoin",
    "dot": "polkadot",
    "matic": "polygon",
    "avax": "avalanche",
    "link": "chainlink",
    "uni": "uniswap",
    "aave": "aave",
    "mkr": "maker",
    "crv": "curve",
    "snx": "synthetix",
    "comp": "compound",
    "ftm": "fantom",
    "atom": "cosmos",
    "near": "near",
    "apt": "aptos",
    "arb": "arbitrum",
    "op": "optimism",
    "sui": "sui",
}


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class GridMatch:
    """Represents a match from The Grid API."""
    matched: bool = False
    entity_id: str = ""
    entity_name: str = ""
    entity_type: str = ""  # profile, product, asset
    description: str = ""
    category: str = ""
    tags: List[str] = field(default_factory=list)
    website: str = ""
    logo_url: str = ""
    tgs_fields: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grid_matched": self.matched,
            "grid_entity_id": self.entity_id,
            "grid_entity_name": self.entity_name,
            "grid_entity_type": self.entity_type,
            "grid_category": self.category,
            "grid_tags": ", ".join(self.tags) if self.tags else "",
            "grid_website": self.website,
            "tgs_recommendation": self._generate_tgs_recommendation()
        }

    def _generate_tgs_recommendation(self) -> str:
        """Generate TGS schema recommendation based on match."""
        if not self.matched:
            return ""

        recommendations = []

        # Based on entity type, recommend TGS fields to populate
        if self.entity_type == "profile":
            recommendations.append(f"Link to Grid Profile: {self.entity_id}")
            if self.category:
                recommendations.append(f"Category: {self.category}")

        if self.tags:
            recommendations.append(f"Tags: {', '.join(self.tags[:5])}")

        if self.website:
            recommendations.append(f"Official URL: {self.website}")

        return " | ".join(recommendations) if recommendations else f"Grid ID: {self.entity_id}"


# =============================================================================
# GRAPHQL QUERIES
# =============================================================================

# Query to search profiles by name
SEARCH_PROFILES_QUERY = """
query SearchProfiles($search: String!) {
  profiles(
    where: {
      _or: [
        { name: { _ilike: $search } },
        { shortDescription: { _ilike: $search } }
      ]
    }
    limit: 5
  ) {
    id
    name
    slug
    shortDescription
    profileType {
      name
    }
    profileTags {
      tag {
        name
      }
    }
    urls {
      url
      urlType {
        name
      }
    }
    logo
  }
}
"""

# Query to search products
SEARCH_PRODUCTS_QUERY = """
query SearchProducts($search: String!) {
  products(
    where: {
      _or: [
        { name: { _ilike: $search } },
        { shortDescription: { _ilike: $search } }
      ]
    }
    limit: 5
  ) {
    id
    name
    shortDescription
    productType {
      name
    }
    productDeployedOnProducts {
      deployedOnProduct {
        name
      }
    }
  }
}
"""

# Query to search assets (tokens)
SEARCH_ASSETS_QUERY = """
query SearchAssets($search: String!) {
  assets(
    where: {
      _or: [
        { name: { _ilike: $search } },
        { ticker: { _ilike: $search } }
      ]
    }
    limit: 5
  ) {
    id
    name
    ticker
    icon
    assetDeployedOnProductAsChain {
      product {
        name
      }
    }
  }
}
"""

# Introspection query to explore schema
INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    types {
      name
      kind
      fields {
        name
        type {
          name
          kind
        }
      }
    }
  }
}
"""


# =============================================================================
# API CLIENT
# =============================================================================

class GridAPIClient:
    """Client for The Grid's GraphQL API."""

    def __init__(self, endpoint: str = GRID_API_ENDPOINT, api_key: str = None):
        self.endpoint = endpoint
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"

    def _execute_query(self, query: str, variables: Dict = None) -> Dict:
        """Execute a GraphQL query."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = self.session.post(
                self.endpoint,
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            result = response.json()

            if "errors" in result:
                print(f"  [!] GraphQL errors: {result['errors']}")
                return {}

            return result.get("data", {})

        except requests.exceptions.RequestException as e:
            print(f"  [!] Grid API request failed: {e}")
            return {}
        except json.JSONDecodeError as e:
            print(f"  [!] Invalid JSON response: {e}")
            return {}

    def search_profiles(self, search_term: str) -> List[Dict]:
        """Search for profiles matching the term."""
        # Use wildcard search
        search = f"%{search_term}%"
        data = self._execute_query(SEARCH_PROFILES_QUERY, {"search": search})
        return data.get("profiles", [])

    def search_products(self, search_term: str) -> List[Dict]:
        """Search for products matching the term."""
        search = f"%{search_term}%"
        data = self._execute_query(SEARCH_PRODUCTS_QUERY, {"search": search})
        return data.get("products", [])

    def search_assets(self, search_term: str) -> List[Dict]:
        """Search for assets (tokens) matching the term."""
        search = f"%{search_term}%"
        data = self._execute_query(SEARCH_ASSETS_QUERY, {"search": search})
        return data.get("assets", [])

    def search_all(self, search_term: str) -> Dict[str, List[Dict]]:
        """Search across all entity types."""
        return {
            "profiles": self.search_profiles(search_term),
            "products": self.search_products(search_term),
            "assets": self.search_assets(search_term)
        }

    def get_schema(self) -> Dict:
        """Get the GraphQL schema via introspection."""
        return self._execute_query(INTROSPECTION_QUERY)


# =============================================================================
# ENTITY MATCHER
# =============================================================================

class GridEntityMatcher:
    """Matches news items to Grid entities."""

    def __init__(self, api_key: str = None):
        self.client = GridAPIClient(api_key=api_key)
        self._cache: Dict[str, GridMatch] = {}

    def extract_keywords(self, text: str) -> List[str]:
        """Extract potential entity names from text."""
        # Common patterns for crypto entities
        keywords = []

        # Look for capitalized words (potential project names)
        caps_pattern = r'\b[A-Z][a-zA-Z]+\b'
        caps_words = re.findall(caps_pattern, text)

        # Filter out common non-entity words
        stop_words = {
            'The', 'This', 'That', 'With', 'From', 'Into', 'Over', 'After',
            'Before', 'About', 'Through', 'During', 'Between', 'Under',
            'Again', 'Further', 'Then', 'Once', 'Here', 'There', 'When',
            'Where', 'Why', 'How', 'All', 'Each', 'Few', 'More', 'Most',
            'Other', 'Some', 'Such', 'Only', 'Own', 'Same', 'Than', 'Too',
            'Very', 'Just', 'Should', 'Now', 'New', 'CEO', 'CTO', 'CFO',
            'USD', 'EUR', 'Million', 'Billion', 'Market', 'Trading', 'Price',
            'Token', 'Crypto', 'Blockchain', 'Network', 'Protocol', 'Fund',
            'Investment', 'Venture', 'Capital', 'Exchange', 'Platform'
        }

        for word in caps_words:
            if word not in stop_words and len(word) > 2:
                keywords.append(word)

        # Look for ticker symbols (all caps, 2-5 chars)
        ticker_pattern = r'\b[A-Z]{2,5}\b'
        tickers = re.findall(ticker_pattern, text)

        for ticker in tickers:
            # Expand known aliases
            if ticker.lower() in NAME_ALIASES:
                keywords.append(NAME_ALIASES[ticker.lower()])
            elif ticker not in stop_words:
                keywords.append(ticker)

        # Look for quoted names
        quoted_pattern = r'"([^"]+)"'
        quoted = re.findall(quoted_pattern, text)
        keywords.extend(quoted)

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower not in seen:
                seen.add(kw_lower)
                unique.append(kw)

        return unique[:5]  # Limit to top 5 keywords

    def match_entity(self, title: str, url: str = "", description: str = "") -> GridMatch:
        """
        Try to match a news item to a Grid entity.

        Returns GridMatch with matched=True if found, along with TGS data.
        """
        # Check cache first
        cache_key = title.lower()[:100]
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Extract keywords to search
        full_text = f"{title} {description}"
        keywords = self.extract_keywords(full_text)

        if not keywords:
            result = GridMatch(matched=False)
            self._cache[cache_key] = result
            return result

        # Try each keyword
        for keyword in keywords:
            # Search across all entity types
            results = self.client.search_all(keyword)

            # Check profiles first (most common)
            if results.get("profiles"):
                profile = results["profiles"][0]
                match = self._create_match_from_profile(profile, keyword)
                self._cache[cache_key] = match
                return match

            # Check products
            if results.get("products"):
                product = results["products"][0]
                match = self._create_match_from_product(product, keyword)
                self._cache[cache_key] = match
                return match

            # Check assets
            if results.get("assets"):
                asset = results["assets"][0]
                match = self._create_match_from_asset(asset, keyword)
                self._cache[cache_key] = match
                return match

        # No match found
        result = GridMatch(matched=False)
        self._cache[cache_key] = result
        return result

    def _create_match_from_profile(self, profile: Dict, keyword: str) -> GridMatch:
        """Create GridMatch from a profile result."""
        # Extract tags
        tags = []
        for pt in profile.get("profileTags", []):
            if pt.get("tag", {}).get("name"):
                tags.append(pt["tag"]["name"])

        # Extract website
        website = ""
        for url_obj in profile.get("urls", []):
            if url_obj.get("urlType", {}).get("name") == "website":
                website = url_obj.get("url", "")
                break

        return GridMatch(
            matched=True,
            entity_id=profile.get("id", ""),
            entity_name=profile.get("name", ""),
            entity_type="profile",
            description=profile.get("shortDescription", ""),
            category=profile.get("profileType", {}).get("name", ""),
            tags=tags,
            website=website,
            logo_url=profile.get("logo", ""),
            confidence=self._calculate_confidence(profile.get("name", ""), keyword)
        )

    def _create_match_from_product(self, product: Dict, keyword: str) -> GridMatch:
        """Create GridMatch from a product result."""
        # Extract deployment info
        deployed_on = []
        for dep in product.get("productDeployedOnProducts", []):
            if dep.get("deployedOnProduct", {}).get("name"):
                deployed_on.append(dep["deployedOnProduct"]["name"])

        return GridMatch(
            matched=True,
            entity_id=product.get("id", ""),
            entity_name=product.get("name", ""),
            entity_type="product",
            description=product.get("shortDescription", ""),
            category=product.get("productType", {}).get("name", ""),
            tags=deployed_on,  # Use deployed-on as tags
            confidence=self._calculate_confidence(product.get("name", ""), keyword)
        )

    def _create_match_from_asset(self, asset: Dict, keyword: str) -> GridMatch:
        """Create GridMatch from an asset result."""
        # Extract chain info
        chains = []
        for chain in asset.get("assetDeployedOnProductAsChain", []):
            if chain.get("product", {}).get("name"):
                chains.append(chain["product"]["name"])

        return GridMatch(
            matched=True,
            entity_id=asset.get("id", ""),
            entity_name=asset.get("name", ""),
            entity_type="asset",
            category=f"Token ({asset.get('ticker', '')})",
            tags=chains,
            logo_url=asset.get("icon", ""),
            confidence=self._calculate_confidence(asset.get("name", ""), keyword)
        )

    def _calculate_confidence(self, entity_name: str, keyword: str) -> float:
        """Calculate match confidence (0-1)."""
        if not entity_name or not keyword:
            return 0.0

        entity_lower = entity_name.lower()
        keyword_lower = keyword.lower()

        # Exact match
        if entity_lower == keyword_lower:
            return 1.0

        # Entity name contains keyword
        if keyword_lower in entity_lower:
            return 0.9

        # Keyword contains entity name
        if entity_lower in keyword_lower:
            return 0.8

        # Partial match (first few chars)
        if entity_lower.startswith(keyword_lower[:3]):
            return 0.6

        return 0.5


# =============================================================================
# INTEGRATION WITH CSV PROCESSOR
# =============================================================================

def enrich_with_grid_data(items: List[Dict], api_key: str = None) -> List[Dict]:
    """
    Enrich extracted items with Grid API data.

    Adds columns:
    - grid_matched: TRUE/FALSE
    - grid_entity_id: The Grid entity ID
    - grid_entity_name: Entity name in The Grid
    - grid_entity_type: profile/product/asset
    - grid_category: Category from The Grid
    - grid_tags: Tags from The Grid
    - tgs_recommendation: Recommended TGS data to use

    Args:
        items: List of extracted items (dicts with 'title', 'url', etc.)
        api_key: Optional Grid API key

    Returns:
        Enriched items with Grid columns added
    """
    print(f"\n[*] Enriching {len(items)} items with Grid data...")

    matcher = GridEntityMatcher(api_key=api_key)
    enriched = []

    for i, item in enumerate(items):
        title = item.get("title", "")
        url = item.get("url", "")
        description = item.get("description", "")

        # Try to match
        match = matcher.match_entity(title, url, description)

        # Add Grid columns to item
        enriched_item = {**item, **match.to_dict()}
        enriched.append(enriched_item)

        if match.matched:
            print(f"  [{i+1}] ✓ {title[:50]}... → {match.entity_name} ({match.entity_type})")
        else:
            print(f"  [{i+1}] ✗ {title[:50]}... → No match")

    matched_count = sum(1 for item in enriched if item.get("grid_matched"))
    print(f"\n[*] Matched {matched_count}/{len(items)} items to Grid entities")

    return enriched


# =============================================================================
# CLI
# =============================================================================

def main():
    """Test The Grid API integration."""
    import argparse

    parser = argparse.ArgumentParser(description="Query The Grid API")
    parser.add_argument("search", nargs="?", help="Search term")
    parser.add_argument("--profiles", action="store_true", help="Search profiles")
    parser.add_argument("--products", action="store_true", help="Search products")
    parser.add_argument("--assets", action="store_true", help="Search assets")
    parser.add_argument("--all", action="store_true", help="Search all (default)")
    parser.add_argument("--schema", action="store_true", help="Show schema")

    args = parser.parse_args()

    client = GridAPIClient()

    if args.schema:
        schema = client.get_schema()
        print(json.dumps(schema, indent=2))
        return

    if not args.search:
        print("Usage: python grid_api.py <search_term>")
        print("       python grid_api.py --schema")
        return

    print(f"\n[*] Searching for: {args.search}\n")

    if args.profiles:
        results = client.search_profiles(args.search)
        print("Profiles:")
        print(json.dumps(results, indent=2))
    elif args.products:
        results = client.search_products(args.search)
        print("Products:")
        print(json.dumps(results, indent=2))
    elif args.assets:
        results = client.search_assets(args.search)
        print("Assets:")
        print(json.dumps(results, indent=2))
    else:
        results = client.search_all(args.search)
        for entity_type, entities in results.items():
            print(f"\n{entity_type.upper()}:")
            for entity in entities:
                name = entity.get("name", entity.get("ticker", "Unknown"))
                eid = entity.get("id", "")
                print(f"  - {name} (ID: {eid})")


if __name__ == "__main__":
    main()
