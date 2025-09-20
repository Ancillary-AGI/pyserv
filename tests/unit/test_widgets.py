"""
Unit tests for Pydance Rich Widgets
"""
import pytest

from pydance.widgets.widgets import RichText, RichSelect, RichTitle
from pydance.widgets.widgets_extra import RichFile, RichDate, RichColor, RichRating


class TestRichTextWidget:
    """Test RichText widget functionality"""

    def test_initialization(self):
        """Test RichText widget initialization"""
        rich_text = RichText(
            name='content',
            format='markdown',
            placeholder='Enter content...',
            value='# Hello World\n\nThis is **markdown** text.',
            theme='dark',
            size='large'
        )

        assert rich_text.name == 'content'
        assert rich_text.format.value == 'markdown'
        assert rich_text.theme.value == 'dark'
        assert rich_text.size.value == 'large'
        assert rich_text.placeholder == 'Enter content...'
        assert rich_text.value == '# Hello World\n\nThis is **markdown** text.'

    def test_render(self):
        """Test RichText widget rendering"""
        rich_text = RichText(
            name='content',
            format='markdown',
            value='# Hello World\n\nThis is **markdown** text.',
            theme='dark'
        )

        html = rich_text.render()
        assert isinstance(html, str)
        assert len(html) > 0
        assert 'Hello World' in html

    def test_validation_empty_content(self):
        """Test RichText validation with empty content"""
        rich_text = RichText(name='content', format='markdown')
        rich_text.set_value('')
        assert not rich_text.validate('')

    def test_validation_valid_content(self):
        """Test RichText validation with valid content"""
        rich_text = RichText(name='content', format='markdown')
        rich_text.set_value('Valid content with enough length')
        assert rich_text.validate('Valid content with enough length')


class TestRichSelectWidget:
    """Test RichSelect widget functionality"""

    def test_initialization(self):
        """Test RichSelect widget initialization"""
        select = RichSelect(
            name='category',
            options=[
                ('tech', 'Technology'),
                ('business', 'Business'),
                ('health', 'Health')
            ],
            placeholder='Select category...',
            searchable=True,
            theme='blue'
        )

        assert select.name == 'category'
        assert len(select.options) == 3
        assert select.searchable is True
        assert select.theme.value == 'blue'
        assert select.placeholder == 'Select category...'

    def test_render(self):
        """Test RichSelect widget rendering"""
        select = RichSelect(
            name='category',
            options=[('tech', 'Technology'), ('business', 'Business')]
        )

        html = select.render()
        assert isinstance(html, str)
        assert len(html) > 0


class TestRichFileWidget:
    """Test RichFile widget functionality"""

    def test_initialization(self):
        """Test RichFile widget initialization"""
        file_widget = RichFile(
            name='files',
            multiple=True,
            accept='image/*,.pdf',
            max_size=5 * 1024 * 1024,  # 5MB
            theme='green'
        )

        assert file_widget.name == 'files'
        assert file_widget.multiple is True
        assert file_widget.accept == 'image/*,.pdf'
        assert file_widget.max_size == 5 * 1024 * 1024
        assert file_widget.theme.value == 'green'

    def test_file_size_formatting(self):
        """Test file size formatting"""
        file_widget = RichFile(name='files', max_size=5 * 1024 * 1024)
        formatted = file_widget._format_file_size(file_widget.max_size)
        assert '5.00 MB' in formatted


class TestRichDateWidget:
    """Test RichDate widget functionality"""

    def test_initialization(self):
        """Test RichDate widget initialization"""
        date_widget = RichDate(
            name='date',
            show_time=True,
            date_format='YYYY-MM-DD',
            time_format='HH:mm',
            theme='purple'
        )

        assert date_widget.name == 'date'
        assert date_widget.show_time is True
        assert date_widget.date_format == 'YYYY-MM-DD'
        assert date_widget.time_format == 'HH:mm'
        assert date_widget.theme.value == 'purple'


class TestRichColorWidget:
    """Test RichColor widget functionality"""

    def test_initialization(self):
        """Test RichColor widget initialization"""
        color_widget = RichColor(
            name='color',
            default_color='#007bff',
            show_palette=True,
            palette=['#ff0000', '#00ff00', '#0000ff', '#ffff00']
        )

        assert color_widget.name == 'color'
        assert color_widget.default_color == '#007bff'
        assert color_widget.show_palette is True
        assert len(color_widget.palette) == 4


class TestRichRatingWidget:
    """Test RichRating widget functionality"""

    def test_initialization(self):
        """Test RichRating widget initialization"""
        rating_widget = RichRating(
            name='rating',
            max_rating=5,
            show_half=True,
            icon='⭐',
            show_value=True
        )

        assert rating_widget.name == 'rating'
        assert rating_widget.max_rating == 5
        assert rating_widget.show_half is True
        assert rating_widget.icon == '⭐'
        assert rating_widget.show_value is True
