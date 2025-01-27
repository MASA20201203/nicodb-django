from django.urls import reverse


def test_index_view_renders_correct_template(client):
    """index ビューが streamings/index.html を使ってレンダリングされることを検証する"""

    # Arrange
    url = reverse("index")

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == 200
    assert "streamings/index.html" in [t.name for t in response.templates]
    assert "Hello, django.nidodb." in response.content.decode()
