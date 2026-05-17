'use client';

import Script from 'next/script';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Loader2 } from 'lucide-react';
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

function GoogleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18A10.96 10.96 0 0 0 1 12c0 1.77.42 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    </svg>
  );
}

export function OAuthButtons({
  onSuccess,
  onError,
  mode = 'sign_in',
}: {
  onSuccess: (pair: TokenPair) => void;
  onError: (msg: string) => void;
  mode?: 'sign_in' | 'sign_up';
}) {
  const [googleReady, setGoogleReady] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const onSuccessRef = useRef(onSuccess);
  const onErrorRef = useRef(onError);
  onSuccessRef.current = onSuccess;
  onErrorRef.current = onError;

  const handleGoogleCredential = useCallback(
    async (response: { credential: string }) => {
      setGoogleLoading(true);
      try {
        const pair = await auth.google(response.credential);
        setToken(pair.access_token);
        if (typeof window !== 'undefined') localStorage.setItem('user', JSON.stringify(pair.user));
        onSuccessRef.current(pair);
      } catch (err: any) {
        onErrorRef.current(err?.message ?? 'Google sign-in failed');
      } finally {
        setGoogleLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;
    const tryInit = () => {
      if (!window.google?.accounts?.id) return false;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleCredential,
        auto_select: false,
      });
      setGoogleReady(true);
      return true;
    };
    if (!tryInit()) {
      const id = window.setInterval(() => { if (tryInit()) window.clearInterval(id); }, 200);
      return () => window.clearInterval(id);
    }
  }, [handleGoogleCredential]);

  const handleGoogleClick = () => {
    if (!window.google?.accounts?.id) return;
    window.google.accounts.id.prompt((notification: any) => {
      if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
        onErrorRef.current('Google sign-in popup was blocked. Please allow popups and try again.');
      }
    });
  };

  // Apple Sign-In
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

  const googleLabel = mode === 'sign_up' ? 'Sign up with Google' : 'Continue with Google';
  const appleLabel = mode === 'sign_up' ? 'Sign up with Apple' : 'Sign in with Apple';

  return (
    <div className="space-y-3">
      {GOOGLE_CLIENT_ID ? (
        <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" />
      ) : null}
      {APPLE_SERVICE_ID ? (
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
      ) : null}

      {APPLE_SERVICE_ID ? (
        <button
          type="button"
          onClick={() => window.AppleID?.auth.signIn()}
          className="w-full flex items-center justify-center gap-3 h-[52px] bg-black text-white rounded-2xl font-semibold text-base hover:bg-black/90 transition-colors"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
          </svg>
          {appleLabel}
        </button>
      ) : null}

      {GOOGLE_CLIENT_ID ? (
        <button
          type="button"
          onClick={handleGoogleClick}
          disabled={!googleReady || googleLoading}
          className="w-full flex items-center justify-center gap-3 h-[52px] bg-white border-2 border-slate-200 text-slate-700 rounded-2xl font-semibold text-base hover:bg-slate-50 hover:border-slate-300 transition-colors disabled:opacity-60"
        >
          {googleLoading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <>
              <GoogleIcon className="w-5 h-5" />
              {googleLabel}
            </>
          )}
        </button>
      ) : null}

      {!GOOGLE_CLIENT_ID && !APPLE_SERVICE_ID ? (
        <p className="text-xs text-slate-400 text-center">
          Set NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID and NEXT_PUBLIC_APPLE_SIGNIN_SERVICE_ID to enable social sign-in.
        </p>
      ) : null}
    </div>
  );
}
