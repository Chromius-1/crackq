import ldap
import logging

from logging.config import fileConfig
from flask import url_for
from saml2 import BINDING_HTTP_POST
from saml2 import BINDING_HTTP_REDIRECT
from saml2 import entity
from saml2.client import Saml2Client
from saml2.config import Config as Saml2Config
import requests


# Setup logging
fileConfig('log_config.ini')
logger = logging.getLogger()

class Saml2():
    """
    SAML2 authentication class

    Arguments
    --------
    meta_url: str
        Location of SAML metadata URL
    meta_file: str
        Location to store metadata locally
    entity_id: str
        SAML entity ID (usually hostname/URL)

    Returns
    ------
    """
    def __init__(self, meta_url, meta_file, entity_id):
        self.meta_url = meta_url
        self.meta_file = meta_file
        self.entity_id = entity_id

    def s_client(self):
        """
        Setup and return the SAML client with specified config
        """
        acs_url = url_for('sso',
                          _scheme='https',
                          _external=True)
        logger.debug('SSO ACS URL: {}'.format(acs_url))
        logout_url = url_for('logout',
                             _scheme='https',
                             _external=True)
        try:
            with open(self.meta_file, 'r') as meta_fh:
                meta_len = len(meta_fh.read())
            if meta_len < 1:
                try:
                    res = requests.get(self.meta_url)
                    with open(self.meta_file, 'w') as meta_fh:
                              meta_fh.write(res.text)
                ###***fix
                except Exception as err:
                    logger.error('Invalid SAML metadata file/s provided:\n{}'.format(
                        err))
                    logger.error('Invalid SAML metadata file/s provided')
        except FileNotFoundError as err:
            res = requests.get(self.meta_url)
            with open(self.meta_file, 'w') as meta_fh:
                      meta_fh.write(res.text)
            #logger.error('Invalid SAML metadata file provided')
        ###***review all of these settings
        settings = {
            'metadata': {
                "local": [self.meta_file]
                },
            'service': {
                'sp': {
                    'name_id_format': 'None',
                    'endpoints': {
                        'assertion_consumer_service': [
                            (acs_url, BINDING_HTTP_REDIRECT),
                            (acs_url, BINDING_HTTP_POST)
                        ],
                        'single_logout_service': [(logout_url, BINDING_HTTP_REDIRECT)]
                    },
                    ###***update some of these if possible
                    'allow_unsolicited': True,
                    #'allow_unknown_attributes': True,
                    'authn_requests_signed': False,
                    'logout_requests_signed': True,
                    'want_assertions_signed': True,
                    'want_response_signed': False,
                    'attribute_map_dir': './attributemaps',
                },
            },
        }
        sp_config = Saml2Config()
        sp_config.load(settings)
        sp_config.entityid = self.entity_id
        sp_config.allow_unknown_attributes = True
        client = Saml2Client(config=sp_config)
        return client

class Ldap():
    def authenticate(uri, username, password):
        try:
            username = ldap.dn.escape_dn_chars(username)
            password = ldap.dn.escape_dn_chars(password)
            conn = ldap.initialize(uri)
            conn.set_option(ldap.OPT_REFERRALS, 0)
            conn.protocol_version = 3
            ###***duplication ehre, review
            #conn.set_option(ldap.OPT_X_TLS,ldap.OPT_X_TLS_DEMAND)
            #conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
            #conn.set_option(ldap.OPT_X_TLS_DEMAND, True )
            conn.set_option(ldap.OPT_DEBUG_LEVEL, 255)
            #conn.start_tls_s()
            ###***Make this configurable from the config file!!!!***
            ldap_base = 'dc=example,dc=org'
            #ldap_base = 'dc=example,dc=org'.format(
            bind = conn.simple_bind_s("cn={},{}".format(
                                    username, ldap_base), password)
            logger.debug('LDAP bind: {}'.format(bind))
            try:
                query = 'cn={}'.format(username)
                result = conn.search_s(ldap_base, 2,
                    query)
                print('RESULT: {}'.format(result))
            except Exception:
                logger.error('Failed to get email address from LDAP')
            conn.unbind_s()
            ###***fix this shit to make it more secure
            return "Success" if 97 in bind else "Failed"
        except ldap.INVALID_CREDENTIALS:
            return "Invalid Credentials"
        except ldap.SERVER_DOWN:
            return "Server down"
        except ldap.LDAPError as err:
            return "Other LDAP error: {}".format(err)
        return "Error"
