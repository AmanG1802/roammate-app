'use client';

import Script from 'next/script';
import { useCallback, useEffect, useRef } from 'react';
import { auth, type TokenPair } from '@/lib/api';
import { setToken } from '@/lib/auth';

declare global {
  interface Window {
    google?: any;
    AppleID?: any;
  }
}

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID ?? '';
const APPLE_SERVICE_ID = process.env.NEXT_PUBLIC_APPLE_SIGNIN_SERVICE_ID ?? '';
const APPLE_REDIRECT_URI =
  process.env.NEXT_PUBLIC_APPLE_SIGNIN_REDIRECT_URI ?? 'http://localhost:3000/auth/callback/apple';

export function OAuthButtons({
  onSuccess,
  onError,
  mode = 'sign_in',
}: {
  onSuccess: (pair: TokenPair) => void;
  onError: (msg: string) => void;
  mode?: 'sign_in' | 'sign_up';
}) {
  const googleBtnRef = useRef<HTMLDivElement>(null);

  const handleGoogleCredential = useCallback(
    async (response: { credential: string }) => {
      try {
        const pair = await auth.google(response.credential);
        setToken(pair.access_token);
        if (typeof window !== 'undefined') localStorage.setItem('user', JSON.stringify(pair.user));
        onSuccess(pair);
      } catch (err: any) {
        onError(err?.message ?? 'Google sign-in failed');
      }
    },
    [onSuccess, onError]
  );

  // Render Google official button once GIS script + container exist
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !googleBtnRef.current) return;
    const tryRender = () => {
      if (!window.google?.accounts?.id) return false;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleCredential,
        auto_select: false,
      });
      window.google.accounts.id.renderButton(googleBtnRef.current!, {
        type: 'standard',
        theme: 'outline',
        size: 'large',
        text: mode === 'sign_up' ? 'signup_with' : 'signin_with',
        shape: 'pill',
        logo_alignment: 'left',
        width: 360,
      });
      return true;
    };
    if (!tryRender()) {
      const id = window.setInterval(() => { if (tryRender()) window.clearInterval(id); }, 200);
      return () => window.clearInterval(id);
    }
  }, [handleGoogleCredential, mode]);

  // Apple Sign-In — listens to a custom event the AppleID JS dispatches
  useEffect(() => {
    if (!APPLE_SERVICE_ID) return;
    const onSuccessEvent = async (event: any) => {
      const id_token = event?.detail?.authorization?.id_token;
      if (!id_token) {
        onError('Apple sign-in did not return an identity token');
        return;
      }
      try {
        const pair = await auth.apple(id_token);
        setToken(pair.access_token);
        if (typeof window !== 'undefined') localStorage.setItem('user', JSON.stringify(pair.user));
        onSuccess(pair);
      } catch (err: any) {
        onError(err?.message ?? 'Apple sign-in failed');
      }
    };
    const onFail = () => onError('Apple sign-in cancelled or failed');
    document.addEventListener('AppleIDSignInOnSuccess', onSuccessEvent);
    document.addEventListener('AppleIDSignInOnFailure', onFail);
    return () => {
      document.removeEventListener('AppleIDSignInOnSuccess', onSuccessEvent);
      document.removeEventListener('AppleIDSignInOnFailure', onFail);
    };
  }, [onSuccess, onError]);

  return (
    <div className="space-y-3">
      {GOOGLE_CLIENT_ID ? (
        <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" />
      ) : null}
      {APPLE_SERVICE_ID ? (
        <>
          <Script
            src="https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js"
            strategy="afterInteractive"
            onLoad={() => {
              if (window.AppleID && APPLE_SERVICE_ID) {
                window.AppleID.auth.init({
                  clientId: APPLE_SERVICE_ID,
                  scope: 'name email',
                  redirectURI: APPLE_REDIRECT_URI,
                  usePopup: true,
                });
              }
            }}
          />
          <meta name="appleid-signin-client-id" content={APPLE_SERVICE_ID} />
          <meta name="appleid-signin-scope" content="name email" />
          <meta name="appleid-signin-redirect-uri" content={APPLE_REDIRECT_URI} />
          <meta name="appleid-signin-use-popup" content="true" />
        </>
      ) : null}

      <div ref={googleBtnRef} className="flex justify-center" />

      {APPLE_SERVICE_ID ? (
        <div
          id="appleid-signin"
          className="w-full h-[44px] cursor-pointer rounded-full overflow-hidden"
          data-color="black"
          data-border="false"
          data-type={mode === 'sign_up' ? 'sign-up' : 'sign-in'}
          data-mode="center-align"
          data-border-radius="22"
        />
      ) : null}

      {!GOOGLE_CLIENT_ID && !APPLE_SERVICE_ID ? (
        <p className="text-xs text-slate-400 text-center">
          Set NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID and NEXT_PUBLIC_APPLE_SIGNIN_SERVICE_ID to enable social sign-in.
        </p>
      ) : null}
    </div>
  );
}
