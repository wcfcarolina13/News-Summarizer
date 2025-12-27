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
    # Separate fields for each entity type
    profile_id: str = ""
    profile_name: str = ""
    product_id: str = ""
    product_name: str = ""
    asset_id: str = ""
    asset_name: str = ""
    asset_ticker: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return Grid match data with separate columns per entity type."""
        return {
            "grid_matched": self.matched,
            "grid_entity_type": self.entity_type if self.matched else "",
            "grid_profile_id": self.profile_id,
            "grid_profile_name": self.profile_name,
            "grid_product_id": self.product_id,
            "grid_product_name": self.product_name,
            "grid_asset_id": self.asset_id,
            "grid_asset_name": self.asset_name,
            "grid_asset_ticker": self.asset_ticker,
            "grid_confidence": round(self.confidence, 2) if self.matched else 0,
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

# Query to search profiles by name (using profileInfos)
SEARCH_PROFILES_QUERY = """
query SearchProfiles($search: String!) {
  profileInfos(
    where: {
      _or: [
        { name: { _contains: $search } },
        { descriptionShort: { _contains: $search } }
      ]
    }
    limit: 10
  ) {
    id
    name
    descriptionShort
    profileType {
      name
    }
    profileSector {
      name
    }
  }
}
"""

# Query to search products
SEARCH_PRODUCTS_QUERY = """
query SearchProducts($search: String!) {
  products(
    where: {
      _or: [
        { name: { _contains: $search } },
        { description: { _contains: $search } }
      ]
    }
    limit: 10
  ) {
    id
    name
    description
    productType {
      name
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
        { name: { _contains: $search } },
        { ticker: { _contains: $search } }
      ]
    }
    limit: 10
  ) {
    id
    name
    ticker
    icon
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
        data = self._execute_query(SEARCH_PROFILES_QUERY, {"search": search_term})
        return data.get("profileInfos", [])

    def search_products(self, search_term: str) -> List[Dict]:
        """Search for products matching the term."""
        data = self._execute_query(SEARCH_PRODUCTS_QUERY, {"search": search_term})
        return data.get("products", [])

    def search_assets(self, search_term: str) -> List[Dict]:
        """Search for assets (tokens) matching the term."""
        data = self._execute_query(SEARCH_ASSETS_QUERY, {"search": search_term})
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
        """
        Extract potential entity names from text.

        IMPORTANT: Only extract names that are likely the PRIMARY SUBJECT of the text,
        not every crypto term mentioned. This prevents matching "Bitcoin" to every
        article that happens to mention Bitcoin.
        """
        keywords = []
        text_lower = text.lower()

        # Only match if the entity appears to be the SUBJECT (at start of title,
        # or is the primary focus based on context)

        # Priority 1: Look for capitalized multi-word names (company/protocol names)
        # These are usually the actual subject
        multi_word_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
        multi_words = re.findall(multi_word_pattern, text)

        stop_phrases = {
            'New York', 'United States', 'Wall Street', 'White House',
            'Hong Kong', 'San Francisco', 'Los Angeles', 'Abu Dhabi',
            'South Korea', 'North America', 'United Kingdom'
        }
        for phrase in multi_words:
            if phrase not in stop_phrases:
                keywords.append(phrase)

        # Priority 2: Look for ticker symbols in context like "$BTC" or "(ETH)"
        ticker_context_pattern = r'[\$\(]([A-Z]{2,5})[\)\s]'
        context_tickers = re.findall(ticker_context_pattern, text)

        for ticker in context_tickers:
            ticker_lower = ticker.lower()
            if ticker_lower in NAME_ALIASES:
                expanded = NAME_ALIASES[ticker_lower]
                if expanded.lower() not in [k.lower() for k in keywords]:
                    keywords.append(expanded)

        # Priority 3: Single capitalized words that appear at the START of the text
        # (likely the subject) - not just anywhere in the text
        first_100_chars = text[:100]  # Expand to 100 chars to catch more subjects
        caps_pattern = r'\b[A-Z][a-z]{2,}\b'
        leading_caps = re.findall(caps_pattern, first_100_chars)

        # Priority 4: All-caps tickers (BTC, ETH, XRP, etc.) anywhere in text
        ticker_pattern = r'\b([A-Z]{2,5})\b'
        tickers_found = re.findall(ticker_pattern, text[:150])

        # Map common tickers to full names for searching
        ticker_map = {
            'BTC': 'Bitcoin', 'ETH': 'Ethereum', 'SOL': 'Solana',
            'XRP': 'XRP', 'ADA': 'Cardano', 'DOGE': 'Dogecoin',
            'DOT': 'Polkadot', 'LINK': 'Chainlink', 'UNI': 'Uniswap',
            'ARB': 'Arbitrum', 'OP': 'Optimism', 'MATIC': 'Polygon',
            'AVAX': 'Avalanche', 'ATOM': 'Cosmos', 'NEAR': 'NEAR',
            'APT': 'Aptos', 'SUI': 'Sui', 'TAO': 'Bittensor',
            'USDT': 'Tether', 'USDC': 'USDC',
        }

        stop_words = {
            # Common words
            'The', 'This', 'That', 'With', 'From', 'Into', 'Over', 'After',
            'Before', 'About', 'Through', 'During', 'Between', 'Under',
            'Again', 'Further', 'Then', 'Once', 'Here', 'There', 'When',
            'Where', 'Why', 'How', 'All', 'Each', 'Few', 'More', 'Most',
            'Other', 'Some', 'Such', 'Only', 'Own', 'Same', 'Than', 'Too',
            'Very', 'Just', 'Should', 'Now', 'New', 'CEO', 'CTO', 'CFO',
            # Business terms (generic - not specific entities)
            'Million', 'Billion', 'Market', 'Trading', 'Price', 'Token',
            'Crypto', 'Blockchain', 'Network', 'Protocol', 'Fund', 'Report',
            'Investment', 'Venture', 'Capital', 'Exchange', 'Platform',
            'Rally', 'Surge', 'Drop', 'Fall', 'Rise', 'Gain', 'Loss',
            'Firm', 'Startup', 'Company', 'Group', 'Digital', 'Global',
            # Days/Months
            'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
            'January', 'February', 'March', 'April', 'May', 'June', 'July',
            'August', 'September', 'October', 'November', 'December',
            # Political/news figures - prevent matching to meme tokens
            'Trump', 'Biden', 'Musk', 'Elon', 'Obama', 'Powell', 'Gensler',
            'Yellen', 'Congress', 'Senate', 'Federal', 'Reserve', 'Government',
            # Common news prefixes/sources
            'Daily', 'Breaking', 'Update', 'Alert', 'News', 'Report',
            # Locations
            'Salvador', 'America', 'Latin',
        }

        for word in leading_caps:
            if word not in stop_words and word.lower() not in [k.lower() for k in keywords]:
                keywords.append(word)

        # Add mapped ticker names
        for ticker in tickers_found:
            if ticker in ticker_map:
                name = ticker_map[ticker]
                if name.lower() not in [k.lower() for k in keywords]:
                    keywords.append(name)

        return keywords[:7]  # Return max 7 keywords - allow more matches

    def match_entity(self, title: str, url: str = "", description: str = "") -> GridMatch:
        """
        Try to match a news item to a Grid entity.

        Returns GridMatch with matched=True if found, along with TGS data.
        Uses fuzzy matching to find the best match across profiles, products, and assets.
        """
        # Check cache first - use title + description for cache key
        full_text = f"{title} {description}"
        cache_key = full_text.lower()[:200]
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Extract keywords to search
        keywords = self.extract_keywords(full_text)

        if not keywords:
            result = GridMatch(matched=False)
            self._cache[cache_key] = result
            return result

        # Collect all candidate matches with scores
        all_candidates: List[Tuple[GridMatch, float]] = []

        for keyword in keywords:
            # Search across all entity types
            results = self.client.search_all(keyword)

            # Score and collect profile matches
            for profile in results.get("profiles", []):
                match = self._create_match_from_profile(profile, keyword)
                score = self._score_match(match.entity_name, keyword, full_text)
                all_candidates.append((match, score))

            # Score and collect product matches
            for product in results.get("products", []):
                match = self._create_match_from_product(product, keyword)
                score = self._score_match(match.entity_name, keyword, full_text)
                all_candidates.append((match, score))

            # Score and collect asset matches
            for asset in results.get("assets", []):
                match = self._create_match_from_asset(asset, keyword)
                score = self._score_match(match.entity_name, keyword, full_text)
                all_candidates.append((match, score))

        if not all_candidates:
            result = GridMatch(matched=False)
            self._cache[cache_key] = result
            return result

        # Sort by score (highest first) and pick the best match
        all_candidates.sort(key=lambda x: x[1], reverse=True)
        best_match, best_score = all_candidates[0]

        # Only accept matches with HIGH confidence (0.7+)
        # This prevents loose matches like "any article mentioning X" -> X entity
        if best_score >= 0.7:
            best_match.confidence = best_score
            self._cache[cache_key] = best_match
            return best_match

        # No good match found
        result = GridMatch(matched=False)
        self._cache[cache_key] = result
        return result

    def _score_match(self, entity_name: str, keyword: str, full_text: str) -> float:
        """
        Score how well an entity matches the keyword and original text.
        Higher score = better match.
        """
        if not entity_name:
            return 0.0

        entity_lower = entity_name.lower()
        keyword_lower = keyword.lower()
        text_lower = full_text.lower()

        score = 0.0

        # Exact name match with keyword (highest priority)
        if entity_lower == keyword_lower:
            score += 1.0
        # Entity name starts with keyword
        elif entity_lower.startswith(keyword_lower):
            score += 0.8
        # Keyword is contained in entity name
        elif keyword_lower in entity_lower:
            score += 0.6
        # Entity name is contained in keyword
        elif entity_lower in keyword_lower:
            score += 0.5

        # Bonus: entity name appears in the original text (confirms relevance)
        if entity_lower in text_lower:
            score += 0.5

        # Bonus: exact word boundary match in text
        import re
        if re.search(r'\b' + re.escape(entity_lower) + r'\b', text_lower):
            score += 0.3

        return min(score, 2.0)  # Cap at 2.0

    def _create_match_from_profile(self, profile: Dict, keyword: str) -> GridMatch:
        """Create GridMatch from a profile result."""
        # Extract sector as tag
        tags = []
        sector = profile.get("profileSector", {})
        if sector and sector.get("name"):
            tags.append(sector["name"])

        profile_id = profile.get("id", "")
        profile_name = profile.get("name", "")

        return GridMatch(
            matched=True,
            entity_id=profile_id,
            entity_name=profile_name,
            entity_type="profile",
            description=profile.get("descriptionShort", ""),
            category=profile.get("profileType", {}).get("name", ""),
            tags=tags,
            confidence=self._calculate_confidence(profile_name, keyword),
            profile_id=profile_id,
            profile_name=profile_name,
        )

    def _create_match_from_product(self, product: Dict, keyword: str) -> GridMatch:
        """Create GridMatch from a product result."""
        product_id = product.get("id", "")
        product_name = product.get("name", "")

        return GridMatch(
            matched=True,
            entity_id=product_id,
            entity_name=product_name,
            entity_type="product",
            description=product.get("description", ""),
            category=product.get("productType", {}).get("name", ""),
            confidence=self._calculate_confidence(product_name, keyword),
            product_id=product_id,
            product_name=product_name,
        )

    def _create_match_from_asset(self, asset: Dict, keyword: str) -> GridMatch:
        """Create GridMatch from an asset result."""
        asset_id = asset.get("id", "")
        asset_name = asset.get("name", "")
        asset_ticker = asset.get("ticker", "")

        return GridMatch(
            matched=True,
            entity_id=asset_id,
            entity_name=asset_name,
            entity_type="asset",
            category=f"Token ({asset_ticker})" if asset_ticker else "Token",
            logo_url=asset.get("icon", ""),
            confidence=self._calculate_confidence(asset_name, keyword),
            asset_id=asset_id,
            asset_name=asset_name,
            asset_ticker=asset_ticker,
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
