/**
 * Keycloak SSO Integration
 */
import Keycloak from 'keycloak-js';

const keycloakConfig = {
  url: import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8080',
  realm: import.meta.env.VITE_KEYCLOAK_REALM || 'bgp-orchestrator',
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'bgp-orchestrator-frontend',
};

export const keycloak = new Keycloak(keycloakConfig);

export const initKeycloak = (): Promise<boolean> => {
  return new Promise((resolve, reject) => {
    keycloak
      .init({
        onLoad: 'check-sso',
        silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html',
        pkceMethod: 'S256',
      })
      .then((authenticated) => {
        resolve(authenticated);
      })
      .catch((error) => {
        reject(error);
      });
  });
};

