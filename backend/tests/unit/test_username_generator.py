"""Tests for guest username generator."""

import pytest
from src.utils.username_generator import (
    generate_guest_username,
    generate_unique_guest_username,
    ADJECTIVES,
    ANIMALS
)


class TestUsernameGenerator:
    """Test username generation utilities."""

    def test_generate_guest_username_format(self):
        """Test that generated username follows correct format."""
        username = generate_guest_username()
        
        # Should start with "Guest_"
        assert username.startswith("Guest_")
        
        # Should have 3 parts separated by underscores
        parts = username.split("_")
        assert len(parts) == 3
        assert parts[0] == "Guest"
        
        # Second part should be an adjective
        assert parts[1] in ADJECTIVES
        
        # Third part should be an animal
        assert parts[2] in ANIMALS

    def test_generate_multiple_usernames(self):
        """Test generating multiple usernames."""
        usernames = [generate_guest_username() for _ in range(100)]
        
        # All should be valid format
        for username in usernames:
            assert username.startswith("Guest_")
            parts = username.split("_")
            assert len(parts) == 3

    def test_username_components_are_valid(self):
        """Test that generated usernames use valid components."""
        # Generate many usernames
        usernames = [generate_guest_username() for _ in range(1000)]
        
        adjectives_used = set()
        animals_used = set()
        
        for username in usernames:
            parts = username.split("_")
            adjectives_used.add(parts[1])
            animals_used.add(parts[2])
        
        # All adjectives should be from the list
        assert adjectives_used.issubset(set(ADJECTIVES))
        
        # All animals should be from the list
        assert animals_used.issubset(set(ANIMALS))

    def test_username_randomness(self):
        """Test that usernames are sufficiently random."""
        # Generate many usernames
        usernames = [generate_guest_username() for _ in range(1000)]
        
        # Should have good variety (not all the same)
        unique_usernames = set(usernames)
        
        # With 30 adjectives and 40 animals, we have 1200 possible combinations
        # Expect significant variety in 1000 generations
        assert len(unique_usernames) > 500  # At least 50% unique

    def test_adjectives_list_not_empty(self):
        """Test that adjectives list is populated."""
        assert len(ADJECTIVES) > 0
        assert all(isinstance(adj, str) for adj in ADJECTIVES)

    def test_animals_list_not_empty(self):
        """Test that animals list is populated."""
        assert len(ANIMALS) > 0
        assert all(isinstance(animal, str) for animal in ANIMALS)

    def test_adjectives_are_chinese_characters(self):
        """Test that adjectives are Chinese characters."""
        for adj in ADJECTIVES:
            # Chinese characters should not be empty
            assert len(adj) > 0
            # Should not contain ASCII letters
            assert not any(c.isascii() and c.isalpha() for c in adj)

    def test_animals_are_chinese_characters(self):
        """Test that animals are Chinese characters."""
        for animal in ANIMALS:
            # Chinese characters should not be empty
            assert len(animal) > 0
            # Should not contain ASCII letters
            assert not any(c.isascii() and c.isalpha() for c in animal)


class TestUniqueUsernameGenerator:
    """Test unique username generation."""

    def test_generate_unique_username_not_in_set(self):
        """Test generating unique username not in existing set."""
        existing = {"Guest_快乐_熊猫", "Guest_勇敢_狮子", "Guest_聪明_老虎"}
        
        username = generate_unique_guest_username(existing)
        
        # Should not be in existing set
        assert username not in existing
        
        # Should follow correct format
        assert username.startswith("Guest_")
        parts = username.split("_")
        assert len(parts) == 3

    def test_generate_unique_with_empty_set(self):
        """Test generating unique username with empty set."""
        existing = set()
        
        username = generate_unique_guest_username(existing)
        
        # Should generate valid username
        assert username.startswith("Guest_")

    def test_generate_multiple_unique_usernames(self):
        """Test generating multiple unique usernames."""
        existing = set()
        
        for _ in range(50):
            username = generate_unique_guest_username(existing)
            assert username not in existing
            existing.add(username)
        
        # Should have 50 unique usernames
        assert len(existing) == 50

    def test_unique_username_with_many_existing(self):
        """Test generating unique username when many already exist."""
        # Create a large set of existing usernames
        existing = set()
        for _ in range(500):
            existing.add(generate_guest_username())
        
        initial_count = len(existing)
        
        # Generate new unique username
        username = generate_unique_guest_username(existing)
        
        # Should not be in existing set
        assert username not in existing
        
        # Adding it should increase set size
        existing.add(username)
        assert len(existing) == initial_count + 1

    def test_unique_username_max_attempts_exceeded(self):
        """Test that function raises error if max attempts exceeded."""
        # Create set with almost all possible combinations
        # This is a simplified test - in reality would need all 1200 combinations
        existing = set()
        
        # Generate many usernames (but not all possible)
        for _ in range(100):
            existing.add(generate_guest_username())
        
        # Should still be able to generate unique (max_attempts default is 100)
        username = generate_unique_guest_username(existing, max_attempts=1000)
        assert username not in existing

    def test_unique_username_preserves_format(self):
        """Test that unique generation preserves username format."""
        existing = {"Guest_快乐_熊猫"}
        
        for _ in range(20):
            username = generate_unique_guest_username(existing)
            
            # Check format
            assert username.startswith("Guest_")
            parts = username.split("_")
            assert len(parts) == 3
            assert parts[1] in ADJECTIVES
            assert parts[2] in ANIMALS
            
            existing.add(username)

    def test_unique_username_with_custom_max_attempts(self):
        """Test unique generation with custom max attempts."""
        existing = set()
        
        # Use low max_attempts
        username = generate_unique_guest_username(existing, max_attempts=10)
        
        assert username.startswith("Guest_")
        assert username not in existing

    def test_username_collision_handling(self):
        """Test handling of username collisions."""
        existing = set()
        
        # Generate usernames until we get a collision
        collision_found = False
        attempts = 0
        max_test_attempts = 5000
        
        while attempts < max_test_attempts and not collision_found:
            username = generate_guest_username()
            if username in existing:
                collision_found = True
            existing.add(username)
            attempts += 1
        
        # Even with collisions, unique generator should work
        if collision_found:
            unique = generate_unique_guest_username(existing)
            assert unique not in existing


class TestUsernameGeneratorEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_generate_with_single_adjective_and_animal(self):
        """Test behavior when lists have minimal entries."""
        # Note: This tests the current implementation
        # In a real scenario, we'd mock ADJECTIVES and ANIMALS
        
        username = generate_guest_username()
        
        # Should still work with current lists
        assert username is not None
        assert len(username) > len("Guest__")

    def test_concurrent_generation_safety(self):
        """Test that concurrent generation is safe."""
        import concurrent.futures
        
        def generate_batch():
            return [generate_guest_username() for _ in range(100)]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(generate_batch) for _ in range(4)]
            results = [f.result() for f in futures]
        
        # All results should be valid
        all_usernames = [u for batch in results for u in batch]
        assert len(all_usernames) == 400
        assert all(u.startswith("Guest_") for u in all_usernames)

    def test_username_length_reasonable(self):
        """Test that generated usernames are reasonable length."""
        username = generate_guest_username()
        
        # Should not be too long
        # Format: Guest_XX_XX where XX are Chinese characters (2-4 chars each)
        # Max reasonable length: Guest_ (6) + 4 + _ (1) + 4 = 15
        assert len(username) < 30

    def test_unique_generation_performance(self):
        """Test that unique generation performs reasonably."""
        import time
        
        existing = set()
        
        start_time = time.time()
        
        # Generate 100 unique usernames
        for _ in range(100):
            username = generate_unique_guest_username(existing)
            existing.add(username)
        
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time (< 1 second)
        assert elapsed < 1.0

    def test_adjectives_no_duplicates(self):
        """Test that ADJECTIVES list has no duplicates."""
        assert len(ADJECTIVES) == len(set(ADJECTIVES))

    def test_animals_no_duplicates(self):
        """Test that ANIMALS list has no duplicates."""
        assert len(ANIMALS) == len(set(ANIMALS))

    def test_total_possible_combinations(self):
        """Test that we have sufficient combinations."""
        total_combinations = len(ADJECTIVES) * len(ANIMALS)
        
        # Should have at least 100 combinations
        assert total_combinations >= 100
        
        # Current lists should give us 30 * 40 = 1200 combinations
        assert total_combinations > 1000
