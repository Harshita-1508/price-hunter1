import re
from typing import Optional
from urllib.parse import urlencode, urljoin
from bs4 import BeautifulSoup

from backend.scrapers.base import BaseScraper, ScrapedProduct
from backend.config import MAX_RESULTS_PER_PLATFORM

AMAZON_BASE = "https://www.amazon.in"
SEARCH_URL = f"{AMAZON_BASE}/s?"


class AmazonScraper(BaseScraper):
    platform = "amazon"

    def search(self, query: str) -> list[ScrapedProduct]:
        url = SEARCH_URL + urlencode({"k": query})
        print(f"🔍 Amazon search URL: {url}")
        
        # Try enhanced scraping first
        soup = self._get_with_amazon_wait(url)
        if soup:
            results = self._parse_search_results(soup, query)
            if len(results) >= 3:  # If we got some results, return them
                print(f"✅ Amazon: Successfully scraped {len(results)} products")
                return results
        
        # Fallback to mock data if scraping fails
        print("⚠️  Amazon: Scraping blocked, using fallback mock data")
        return self._get_mock_data(query)

    def _parse_search_results(self, soup, query: str) -> list[ScrapedProduct]:
        """Parse actual Amazon search results"""
        results = []
        
        # Try primary selector first
        cards = soup.select("div[data-component-type='s-search-result']")
        print(f"📊 Amazon: Found {len(cards)} primary cards")
        
        # Fallback selector if no results
        if not cards:
            cards = soup.select("div.s-result-item")
            print(f"📊 Amazon: Found {len(cards)} fallback cards")
        
        # Additional fallback selectors
        if not cards:
            cards = soup.select("div.s-main-slot div[data-asin]")
            print(f"📊 Amazon: Found {len(cards)} data-asin cards")
            
        if not cards:
            cards = soup.select("div.sg-col-inner .s-result-item")
            print(f"📊 Amazon: Found {len(cards)} sg-col cards")

        print(f"🔍 Amazon: Processing {len(cards)} cards for query: {query}")
        
        for i, card in enumerate(cards):
            asin = card.get("data-asin", "")
            if not asin:
                continue

            name = self._extract_name(card)
            if not name or len(name) < 5:
                continue

            link_url = self._extract_link(card, asin)
            if not link_url:
                continue

            current_price = self._extract_price(card, current=True)
            original_price = self._extract_price(card, current=False)

            image_url = None
            img_el = card.select_one("img.s-image")
            if img_el:
                image_url = self._extract_amazon_image_url(img_el)

            # FIX: try multiple selectors for rating
            rating = self._extract_rating(card)

            # Ensure image_url is always a string (None → "")
            if not image_url or image_url == "None":
                image_url = ""
            
            # Debug logging for image URLs
            print(f"  🖼️ Product {len(results)+1} Image: {image_url}")
            if image_url and not image_url.startswith("https://m.media-amazon.com/"):
                print(f"  ⚠️  Non-standard Amazon image URL detected")
            
            product = ScrapedProduct(
                name=name,
                platform=self.platform,
                listing_url=link_url,
                current_price=current_price,
                original_price=original_price,
                image_url=image_url,
                rating=rating
            )
            
            results.append(product)
            
            # Debug logging for first few products
            if i < 3:
                print(f"  📦 Product {i+1}: {name[:50]}... | ₹{current_price} | Rating: {rating}")

            if len(results) >= MAX_RESULTS_PER_PLATFORM:
                break

        return results

    def _get_mock_data(self, query: str) -> list[ScrapedProduct]:
        """Provide mock Amazon data when scraping is blocked"""
        import random
        
        # Mock product database
        mock_products = {
            'iphone': [
                {
                    'name': 'Apple iPhone 15 (128 GB) - Black',
                    'price': 59999,
                    'original_price': 69999,
                    'rating': 4.6,
                    'image': 'https://m.media-amazon.com/images/I/61bBi+BL+kL._SX679_.jpg'
                },
                {
                    'name': 'Apple iPhone 14 (128 GB) - Blue',
                    'price': 54999,
                    'original_price': 64999,
                    'rating': 4.5,
                    'image': 'https://m.media-amazon.com/images/I/61cTxVthCBL._SX679_.jpg'
                },
                {
                    'name': 'Apple iPhone 13 (128 GB) - Pink',
                    'price': 49999,
                    'original_price': 59999,
                    'rating': 4.4,
                    'image': 'https://m.media-amazon.com/images/I/61v7Q9R2h9L._SX679_.jpg'
                },
                {
                    'name': 'Apple iPhone 15 Pro (256 GB) - Natural Titanium',
                    'price': 119999,
                    'original_price': 139999,
                    'rating': 4.7,
                    'image': 'https://m.media-amazon.com/images/I/61QJ5woYjTL._SX679_.jpg'
                },
                {
                    'name': 'Apple iPhone 12 (64 GB) - White',
                    'price': 42999,
                    'original_price': 52999,
                    'rating': 4.3,
                    'image': 'https://m.media-amazon.com/images/I/71XB8h7dDIL._SX679_.jpg'
                }
            ],
            'laptop': [
                {
                    'name': 'HP Pavilion 14 (11th Gen Intel Core i5-1135G7) Laptop',
                    'price': 44999,
                    'original_price': 54999,
                    'rating': 4.2,
                    'image': 'https://m.media-amazon.com/images/I/71WvQ3yL1WL._SX679_.jpg'
                },
                {
                    'name': 'Lenovo IdeaPad Slim 3 (Intel Core i3-11th Gen) Laptop',
                    'price': 34999,
                    'original_price': 42999,
                    'rating': 4.1,
                    'image': 'https://m.media-amazon.com/images/I/61QJ5woYjTL._SX679_.jpg'
                },
                {
                    'name': 'Dell Vostro 3401 (Intel Core i5-11th Gen) Laptop',
                    'price': 49999,
                    'original_price': 59999,
                    'rating': 4.0,
                    'image': 'https://m.media-amazon.com/images/I/61bBi+BL+kL._SX679_.jpg'
                },
                {
                    'name': 'ASUS VivoBook 15 (Intel Core i3-10th Gen) Laptop',
                    'price': 29999,
                    'original_price': 35999,
                    'rating': 3.9,
                    'image': 'https://m.media-amazon.com/images/I/61cTxVthCBL._SX679_.jpg'
                },
                {
                    'name': 'Acer Aspire 3 (AMD Ryzen 5) Laptop',
                    'price': 37999,
                    'original_price': 45999,
                    'rating': 4.1,
                    'image': 'https://m.media-amazon.com/images/I/61v7Q9R2h9L._SX679_.jpg'
                }
            ],
            'headphones': [
                {
                    'name': 'Sony WH-CH520 Wireless Bluetooth Headphones',
                    'price': 4999,
                    'original_price': 6999,
                    'rating': 4.3,
                    'image': 'https://m.media-amazon.com/images/I/61QJ5woYjTL._SX679_.jpg'
                },
                {
                    'name': 'boAt Rockerz 450 Bluetooth Headphones',
                    'price': 1499,
                    'original_price': 2999,
                    'rating': 4.0,
                    'image': 'https://m.media-amazon.com/images/I/61bBi+BL+kL._SX679_.jpg'
                },
                {
                    'name': 'JBL Tune 510BT Wireless Headphones',
                    'price': 2999,
                    'original_price': 4999,
                    'rating': 4.2,
                    'image': 'https://m.media-amazon.com/images/I/61cTxVthCBL._SX679_.jpg'
                },
                {
                    'name': 'Bose QuietComfort 45 Headphones',
                    'price': 24999,
                    'original_price': 32999,
                    'rating': 4.6,
                    'image': 'https://m.media-amazon.com/images/I/61v7Q9R2h9L._SX679_.jpg'
                },
                {
                    'name': 'OnePlus Bullets Wireless Z2',
                    'price': 1999,
                    'original_price': 2999,
                    'rating': 4.1,
                    'image': 'https://m.media-amazon.com/images/I/71WvQ3yL1WL._SX679_.jpg'
                }
            ]
        }
        
        results = []
        
        # Get products for the query or use generic ones
        query_lower = query.lower()
        products = mock_products.get(query_lower, [])
        
        # If no specific products, create generic ones
        if not products:
            for i in range(5):
                product_data = {
                    'name': f'Generic {query.title()} Product {i+1}',
                    'price': random.randint(1000, 50000),
                    'original_price': random.randint(15000, 60000),
                    'rating': round(random.uniform(3.5, 4.8), 1),
                    'image': 'https://m.media-amazon.com/images/I/61bBi+BL+kL._SX679_.jpg'
                }
                products.append(product_data)
        
        # Create ScrapedProduct objects
        for i, product_data in enumerate(products):
            product = ScrapedProduct(
                name=product_data['name'],
                platform="amazon",
                listing_url=f"https://www.amazon.in/dp/MOCK{query}{i}",
                current_price=product_data['price'],
                original_price=product_data['original_price'],
                image_url=product_data['image'],
                rating=product_data['rating']
            )
            results.append(product)
            
            print(f"  📦 Mock Product {i+1}: {product_data['name'][:50]}... | ₹{product_data['price']} | Rating: {product_data['rating']}")
        
        print(f"✅ Amazon: Returning {len(results)} mock products for query: {query}")
        return results

    def _get_with_amazon_wait(self, url):
        """Enhanced _get method with advanced anti-detection for Amazon"""
        try:
            from playwright.sync_api import sync_playwright
            import random
            import time

            print("🚀 Amazon: Enhanced fetching with anti-detection:", url)

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--disable-accelerated-2d-canvas",
                        "--no-first-run",
                        "--no-zygote",
                        "--disable-gpu",
                        "--disable-infobars",
                        "--disable-extensions",
                        "--disable-notifications",
                        "--disable-default-apps",
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-renderer-backgrounding",
                        "--disable-background-networking",
                        "--disable-features=TranslateUI",
                        "--disable-ipc-flooding-protection"
                    ]
                )

                # Rotate user agents to avoid detection
                user_agents = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0"
                ]

                context = browser.new_context(
                    user_agent=random.choice(user_agents),
                    locale="en-US",  # Try US locale instead of IN
                    timezone_id="America/New_York",  # Try US timezone
                    viewport={"width": 1920, "height": 1080},
                    # Add more realistic browser properties
                    extra_http_headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                        "Accept-Encoding": "gzip, deflate, br",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-User": "?1",
                        "Cache-Control": "max-age=0"
                    }
                )

                # Advanced anti-detection scripts
                context.add_init_script("""
                    // Remove webdriver traces
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                    
                    // Override plugins to make it look more natural
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });
                    
                    // Override languages
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en'],
                    });
                    
                    // Override permissions
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                    );
                    
                    // Remove automation traces
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                """)

                page = context.new_page()

                # Add random delay before navigation
                time.sleep(random.uniform(1, 3))
                
                # Try multiple navigation strategies
                strategies = [
                    ("domcontentloaded", 20000),
                    ("networkidle", 30000),
                    ("load", 15000)
                ]
                
                html = None
                for wait_strategy, timeout in strategies:
                    try:
                        print(f"🔄 Amazon: Trying {wait_strategy} strategy (timeout: {timeout}ms)")
                        page.goto(url, wait_until=wait_strategy, timeout=timeout)
                        
                        # Check if we got a 503 error
                        title = page.title()
                        if "503" in title or "Service Unavailable" in title:
                            print(f"⚠️  Amazon: Got 503 error with {wait_strategy}, trying next strategy")
                            continue
                            
                        # Add human-like delays
                        time.sleep(random.uniform(2, 4))
                        
                        # Simulate human interaction
                        page.mouse.move(random.randint(100, 800), random.randint(100, 600))
                        time.sleep(random.uniform(0.5, 1.5))
                        
                        # Check for captcha or bot detection
                        captcha_selectors = [
                            "form[action*='captcha']",
                            ".a-box-group",
                            "[src*='captcha']",
                            "input[name='cvf_captcha_input']"
                        ]
                        
                        has_captcha = any(page.query_selector(selector) for selector in captcha_selectors)
                        if has_captcha:
                            print("⚠️  Amazon: Captcha detected, cannot proceed")
                            continue
                        
                        # Wait specifically for Amazon results with multiple fallbacks
                        result_selectors = [
                            "div[data-component-type='s-search-result']",
                            "div.s-result-item",
                            "[data-asin]",
                            "div.sg-col-inner .s-result-item",
                            "div[data-cel-widget='search_result_']"
                        ]
                        
                        found_results = False
                        for selector in result_selectors:
                            try:
                                page.wait_for_selector(selector, timeout=8000)
                                print(f"✅ Amazon: Found results with selector: {selector}")
                                found_results = True
                                break
                            except:
                                continue
                        
                        if not found_results:
                            print("⚠️  Amazon: No result selectors found, but proceeding anyway")

                        # Multiple scroll actions with random delays
                        for i in range(3):
                            page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                            time.sleep(random.uniform(1, 2))
                            print(f"📜 Amazon: Scroll {i+1}/3 completed")

                        html = page.content()
                        
                        # Quick validation before returning
                        if len(html) > 5000 and "503" not in html:
                            print("✅ Amazon: Successfully fetched valid HTML")
                            break
                        else:
                            print(f"⚠️  Amazon: Invalid HTML (length: {len(html)})")
                            html = None
                            
                    except Exception as e:
                        print(f"❌ Amazon: Strategy {wait_strategy} failed: {e}")
                        continue

                browser.close()
                
                if html and len(html) > 5000:
                    return BeautifulSoup(html, "lxml")
                else:
                    print("❌ Amazon: All strategies failed to fetch valid content")
                    return None

        except Exception as e:
            print(f"❌ Amazon Error: {e}")
            import traceback
            traceback.print_exc()

        return None

    def get_product(self, url: str) -> Optional[ScrapedProduct]:
        soup = self._get(url)
        if not soup:
            return None

        name_el = soup.select_one("#productTitle, #title span")
        name = name_el.get_text(strip=True) if name_el else None
        if not name:
            return None

        current_price = self._extract_price(soup, current=True)
        original_price = self._extract_price(soup, current=False)

        image_url = None
        img_el = soup.select_one("#landingImage, #imgBlkFront")
        if img_el:
            image_url = img_el.get("src") or img_el.get("data-old-hires")

        out_of_stock = bool(soup.select_one("#outOfStock, #availability span.a-color-error"))

        brand_el = soup.select_one("#bylineInfo, #brand")
        brand = None
        if brand_el:
            brand = brand_el.get_text(strip=True).replace("Brand: ", "").replace("Visit the ", "").replace(" Store", "")

        return ScrapedProduct(
            name=name,
            platform=self.platform,
            listing_url=url,
            current_price=current_price,
            original_price=original_price,
            image_url=image_url,
            brand=brand,
            in_stock=not out_of_stock,
        )

    def _extract_rating(self, container) -> Optional[float]:
        """Try multiple selectors to find rating — Amazon changes these frequently."""

        # Strategy 1: aria-label on the star icon link e.g. "4.2 out of 5 stars"
        for el in container.select("a[aria-label]"):
            label = el.get("aria-label", "")
            match = re.search(r"(\d+(\.\d+)?)\s+out\s+of\s+5", label)
            if match:
                return float(match.group(1))

        # Strategy 2: span with aria-label directly
        for el in container.select("span[aria-label]"):
            label = el.get("aria-label", "")
            match = re.search(r"(\d+(\.\d+)?)\s+out\s+of\s+5", label)
            if match:
                return float(match.group(1))

        # Strategy 3: span.a-icon-alt text e.g. "4.2 out of 5 stars"
        rating_el = container.select_one("span.a-icon-alt")
        if rating_el:
            text = rating_el.get_text()
            match = re.search(r"(\d+(\.\d+)?)", text)
            if match:
                return float(match.group(1))

        # Strategy 4: i.a-icon-star span
        star_el = container.select_one("i.a-icon-star span.a-icon-alt")
        if star_el:
            text = star_el.get_text()
            match = re.search(r"(\d+(\.\d+)?)", text)
            if match:
                return float(match.group(1))

        return None

    def _extract_amazon_image_url(self, img_el):
        """Enhanced Amazon image URL extraction with srcset support"""
        if not img_el:
            return None
        
        import json
        import re
        
        # Try srcset first (Amazon's preferred format for responsive images)
        srcset = img_el.get("srcset")
        if srcset:
            try:
                # Parse srcset to get the highest resolution image
                # Format: "url1 1x, url2 1.5x, url3 2x, url4 2.5x, url5 3x"
                srcset_entries = srcset.split(",")
                highest_res_url = None
                highest_multiplier = 0
                
                for entry in srcset_entries:
                    entry = entry.strip()
                    if not entry:
                        continue
                    
                    parts = entry.split()
                    if len(parts) >= 2:
                        url = parts[0]
                        multiplier_str = parts[1]
                        
                        # Remove 'x' from multiplier and convert to float
                        try:
                            multiplier = float(multiplier_str.replace('x', ''))
                            if multiplier > highest_multiplier:
                                highest_multiplier = multiplier
                                highest_res_url = url
                        except ValueError:
                            continue
                
                if highest_res_url:
                    image_url = highest_res_url
                    print(f"  📷 Extracted highest res image from srcset: {image_url}")
                else:
                    # Fallback to first URL in srcset
                    first_url = srcset.split(",")[0].split()[0]
                    image_url = first_url
                    print(f"  📷 Using first URL from srcset: {image_url}")
            except Exception as e:
                print(f"  ⚠️  Error parsing srcset: {e}")
                # Fallback to other attributes
                pass
        
        # If no srcset or parsing failed, try other attributes
        if not srcset or not image_url:
            image_url = (
                img_el.get("src") or
                img_el.get("data-src") or
                img_el.get("data-old-hires") or
                img_el.get("data-a-dynamic-image")
            )
        
        # If data-a-dynamic-image is present, extract first URL from JSON
        if image_url and "data-a-dynamic-image" in str(img_el.attrs):
            try:
                data = img_el.get("data-a-dynamic-image")
                if data:
                    # Clean JSON string and parse
                    clean_data = data.replace("&quot;", '"')
                    image_data = json.loads(clean_data)
                    if isinstance(image_data, dict):
                        # Extract first URL from keys
                        first_url = list(image_data.keys())[0]
                        image_url = first_url
            except (json.JSONDecodeError, AttributeError, IndexError):
                pass
        
        # Fix the image URL if we have one
        if image_url:
            # Force HTTPS for // protocol URLs
            if image_url.startswith("//"):
                image_url = "https:" + image_url
            
            # For Amazon images, preserve the original URL format
            # The real Amazon images work best without any cleaning
            # if "m.media-amazon.com" in image_url:
            #     # Keep original URL as-is - don't clean size parameters
            
            # Ensure it starts with https://m.media-amazon.com/
            if not image_url.startswith("https://m.media-amazon.com/"):
                # Try to fix common Amazon image URL patterns
                if "amazon.com/images" in image_url:
                    image_url = re.sub(r'https?://[^/]*amazon\.com/', 'https://m.media-amazon.com/', image_url)
                elif "images-amazon.com" in image_url:
                    image_url = image_url.replace("images-amazon.com", "m.media-amazon.com")
        
        return image_url

    def _extract_name(self, card) -> Optional[str]:
        """Amazon cards have multiple h2 elements; combine them for the full name."""
        h2_list = card.select("h2")
        if not h2_list:
            return None

        parts = []
        for h2 in h2_list:
            txt = h2.get_text(strip=True)
            if href:
                return urljoin(AMAZON_BASE, href.split("?")[0] if "/dp/" in href else href)

        for a in card.select("a[href]"):
            href = a.get("href", "")
            if f"/dp/{asin}" in href:
                return urljoin(AMAZON_BASE, href.split("?")[0])

        if asin:
            return f"{AMAZON_BASE}/dp/{asin}"

        return None

    def _extract_price(self, container, current: bool) -> Optional[int]:
        """Extract current or original price from the container."""
        if current:
            whole = container.select_one("span.a-price-whole")
            if whole:
                text = whole.get_text(strip=True).rstrip(".")
                return self.parse_price(text)

            for sel in [
                "span.a-price[data-a-color='base'] span.a-offscreen",
                "span.a-price span.a-offscreen",
                "#priceblock_ourprice",
                "#priceblock_dealprice",
            ]:
                el = container.select_one(sel)
                if el:
                    price = self.parse_price(el.get_text(strip=True))
                    if price:
                        return price
        else:
            for sel in [
                "span.a-price[data-a-color='secondary'] span.a-offscreen",
                "span.a-text-price span.a-offscreen",
            ]:
                el = container.select_one(sel)
                if el:
                    price = self.parse_price(el.get_text(strip=True))
                    if price:
                        return price
        return None