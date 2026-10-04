import pytest
from app.models.product import Product
from app.adapters.suppliers.image_search_provider import MockImageSearchProvider
from app.services.image_matching_service import ImageMatchingService, is_valid_image_url


def test_image_matching_verified_above_threshold(db_session):
    """
    Feature 4: Candidate image title matches product title above threshold -> image attached & verified.
    """
    ImageMatchingService.clear_cache()
    MockImageSearchProvider.clear_seeds()
    valid_upc = "012345678905"
    MockImageSearchProvider.seed_upc_result(
        "0012345678905",
        [
            {
                "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c",
                "title": "CAT6 Ethernet Cable 10ft Blue Patch Cord",
                "brand": "Axiom",
                "source": "mock_google"
            }
        ]
    )

    product = Product(
        sku="TEST-CAT6-CBL",
        title="CAT6 550MHz Ethernet Cable Blue 10ft",
        brand="Axiom",
        upc=valid_upc,
        images=[]
    )
    db_session.add(product)
    db_session.commit()

    service = ImageMatchingService(db=db_session, provider=MockImageSearchProvider())
    result = service.match_product_image_by_upc(product, threshold=0.50)

    assert result.status == "verified"
    assert result.chosen_image_url == "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c"
    assert result.similarity_score >= 0.50
    assert result.source == "mock_google"
    assert len(product.images) > 0
    assert product.images[0] == result.chosen_image_url
    assert product.specs_json.get("image_status") == "verified"


def test_image_matching_rejects_mismatch_and_marks_needs_review(db_session):
    """
    Feature 4: When UPC search returns an iPhone photo for a cable product,
    it must NOT attach the image, must NOT crash, and must mark 'image_needs_review'.
    """
    ImageMatchingService.clear_cache()
    MockImageSearchProvider.clear_seeds()
    valid_upc = "097855149367"
    # Seed contradictory consumer result (iPhone for connector UPC)
    MockImageSearchProvider.seed_upc_result(
        valid_upc,
        [
            {
                "image_url": "https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5",
                "title": "Apple iPhone 12 Pro Max 128GB Space Gray Unlocked",
                "brand": "Apple",
                "source": "consumer_barcode_db"
            }
        ]
    )

    product = Product(
        sku="WILSON-SMA-CONN",
        title="N-Female to SMA-Male RF Coaxial Adapter Connector",
        brand="Wilson Electronics",
        upc=valid_upc,
        images=[]
    )
    db_session.add(product)
    db_session.commit()

    service = ImageMatchingService(db=db_session, provider=MockImageSearchProvider())
    result = service.match_product_image_by_upc(product, threshold=0.60)

    assert result.status == "image_needs_review"
    assert result.chosen_image_url is None
    # Product images must remain empty (no wrong iPhone image attached!)
    assert len(product.images) == 0
    assert product.specs_json.get("image_status") == "image_needs_review"
    assert "image_review_reason" in product.specs_json
    assert len(product.specs_json.get("image_candidates", [])) > 0


def test_image_url_validation():
    """
    Feature 4: Validate image URLs are reachable and clean.
    """
    # Bad URLs
    assert not is_valid_image_url("")
    assert not is_valid_image_url("not_a_url")
    assert not is_valid_image_url("ftp://example.com/image.png")
    assert not is_valid_image_url("https://example.com/placeholder.png")
    assert not is_valid_image_url("https://example.com/no_image_available.jpg")

    # Valid test/mock URLs
    assert is_valid_image_url("https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c")
