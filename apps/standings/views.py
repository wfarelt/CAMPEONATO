from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from datetime import datetime

from apps.core.categories import get_request_championship_category, CHAMPIONSHIP_CATEGORY_CHOICES
from apps.standings.services import build_standings


def standings_view(request):
    category = get_request_championship_category(request)
    return render(
        request,
        "standings/standings.html",
        {"standings": build_standings(category=category, include_adjustments=True)},
    )


def standings_api(request):
    category = get_request_championship_category(request)
    return JsonResponse({"standings": build_standings(category=category, include_adjustments=False)})


def standings_sitemap(request):
    """Generate XML sitemap for standings pages."""
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    # Add standings page for each category
    for category_code, category_label in CHAMPIONSHIP_CATEGORY_CHOICES:
        url = request.build_absolute_uri(f'/standings/?category={category_code}')
        last_mod = datetime.now().strftime('%Y-%m-%d')
        xml_content += f'  <url>\n'
        xml_content += f'    <loc>{url}</loc>\n'
        xml_content += f'    <lastmod>{last_mod}</lastmod>\n'
        xml_content += f'    <priority>0.8</priority>\n'
        xml_content += f'  </url>\n'
    
    xml_content += '</urlset>'
    return HttpResponse(xml_content, content_type='application/xml')
