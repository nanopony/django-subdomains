from django.http import Http404
from django.utils.module_loading import import_string
import operator
import logging
import re
from django.conf import settings
from django.utils.cache import patch_vary_headers

logger = logging.getLogger('django')
lower = operator.methodcaller('lower')

UNSET = object()

main_domain_regex = re.compile(r'^(?:(?P<subdomain>.*?)\.)?%s(?::.*)?$' % re.escape(settings.MAIN_DOMAIN.lower()))

try:
    virtualhost_to_urlconf = import_string(settings.VIRTUALHOST_URLCONF_RESOLVER_FUNC)
except AttributeError:
    virtualhost_to_urlconf = lambda q: False

class SubdomainURLRoutingMiddleware():
    """
    A middleware class that allows for subdomain-based URL routing.
    """
    def process_request(self, request):
        """
        Sets the current request's ``urlconf`` attribute to the urlconf
        associated with the subdomain, if it is listed in
        ``settings.SUBDOMAIN_URLCONFS``.
        """

        host = request.get_host().lower()
        matches = main_domain_regex.match(host)
        if matches:
            request.subdomain = matches.group('subdomain')
            if request.subdomain is not UNSET:
                urlconf = settings.SUBDOMAIN_URLCONFS.get(request.subdomain)
                if urlconf is not None:
                    request.urlconf = urlconf
        else:
            request.subdomain = None
            urlconf = virtualhost_to_urlconf(host)
            if urlconf is False:
                logger.error('Attempt to access %s as hostname; Ignored;' % host)
                raise Http404
            request.host = host
            request.urlconf = urlconf




    def process_response(self, request, response):
        """
        Forces the HTTP ``Vary`` header onto requests to avoid having responses
        cached across subdomains.
        """
        if getattr(settings, 'FORCE_VARY_ON_HOST', True):
            patch_vary_headers(response, ('Host',))

        return response
