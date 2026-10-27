import numpy as np
import pytest

from nkdem.stats import assign_blocks, difference_stats, nmad, poly_terms, polynomial_matrix


def test_nmad_matches_definition():
    values = np.array([1.0, 2.0, 3.0, 4.0, 100.0])
    median = np.median(values)
    expected = 1.4826 * np.median(np.abs(values - median))
    assert nmad(values) == pytest.approx(expected)


def test_nmad_ignores_nan_and_empty():
    assert nmad(np.array([np.nan, np.nan])) != nmad(np.array([np.nan]))
    assert np.isnan(nmad(np.array([np.nan])))


def test_difference_stats_respects_mask_and_nan():
    diff = np.array([[1.0, 2.0], [3.0, np.nan]])
    mask = np.array([[True, True], [False, False]])
    median, mad, count = difference_stats(diff, mask)
    assert count == 2
    assert median == pytest.approx(1.5)
    assert mad > 0


def test_poly_terms_order_two():
    # Base tensor-producto: (order + 1)**2 = 9 términos para order=2.
    assert poly_terms(2) == [
        (0, 0), (0, 1), (0, 2),
        (1, 0), (1, 1), (1, 2),
        (2, 0), (2, 1), (2, 2),
    ]


def test_polynomial_matrix_shape_and_values():
    x = np.array([2.0])
    y = np.array([3.0])
    matrix = polynomial_matrix(x, y, 2)
    assert matrix.shape == (1, 9)
    # Términos: [1, y, y², x, xy, xy², x², x²y, x²y²]
    np.testing.assert_allclose(matrix[0], [1, 3, 9, 2, 6, 18, 4, 12, 36])


def test_assign_blocks_marks_grid_cells():
    mask = np.ones((4, 4), dtype=bool)
    blocks = assign_blocks(mask, n_blocks=2)
    assert set(np.unique(blocks)) == {0, 1, 2, 3}
    assert blocks[0, 0] == 0
    assert blocks[3, 3] == 3
    assert np.all(assign_blocks(np.zeros((2, 2), dtype=bool), 2) == -1)
