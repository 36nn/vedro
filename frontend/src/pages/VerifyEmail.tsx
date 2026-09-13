/**
 * /verify-email?token=... — подтверждение email по ссылке из письма.
 *
 * Состояния: проверка / успех / истёкшая ссылка / уже подтверждён /
 * недействительная ссылка / нет связи с сервером.
 */

import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError, resendVerification, verifyEmail } from "../services/api";

type VerifyState =
  | "checking"
  | "success"
  | "expired"
  | "used"
  | "invalid"
  | "network";

function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const [state, setState] = useState<VerifyState>("checking");
  const [verifiedEmail, setVerifiedEmail] = useState<string | null>(null);

  // Повторная отправка (актуально для истёкшей ссылки)
  const [resendEmail, setResendEmail] = useState("");
  const [resendState, setResendState] = useState<
    "idle" | "sending" | "sent" | "error"
  >("idle");
  const [resendMessage, setResendMessage] = useState<string | null>(null);
  // Ссылка подтверждения — только в dev-режиме (письма не шлются)
  const [devLink, setDevLink] = useState<string | null>(null);

  // StrictMode монтирует эффекты дважды — подтверждаем только один раз
  const ranRef = useRef(false);

  useEffect(() => {
    if (ranRef.current) return;
    ranRef.current = true;

    const token = searchParams.get("token");
    if (!token) {
      setState("invalid");
      return;
    }

    verifyEmail(token)
      .then((result) => {
        setVerifiedEmail(result.email);
        setState("success");
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError) {
          if (err.status === 410) setState("expired");
          else if (err.status === 409) setState("used");
          else setState("invalid");
        } else {
          setState("network");
        }
      });
  }, [searchParams]);

  async function handleResend() {
    if (resendState === "sending") return;
    setResendState("sending");
    setResendMessage(null);
    try {
      const result = await resendVerification(resendEmail.trim());
      setResendState("sent");
      setResendMessage(result.message);
      setDevLink(result.verification_url ?? null);
    } catch (err) {
      setResendState("error");
      setResendMessage(err instanceof Error ? err.message : "Не удалось отправить письмо");
    }
  }

  const titles: Record<VerifyState, string> = {
    checking: "Подтверждаем email…",
    success: "Email успешно подтверждён!",
    expired: "Ссылка подтверждения истекла.",
    used: "Email уже был подтверждён.",
    invalid: "Недействительная ссылка подтверждения.",
    network: "Нет связи с сервером.",
  };

  return (
    <main className="page page--centered">
      <section className="auth-card">
        <h1 className="auth-card__title">{titles[state]}</h1>

        {state === "checking" && (
          <p className="home__loading">
            <span className="spinner" />
            Проверяем ссылку…
          </p>
        )}

        {state === "success" && (
          <>
            <p className="register-note">
              {verifiedEmail ? (
                <>
                  Аккаунт <b className="register-note__email">{verifiedEmail}</b>{" "}
                  активирован.
                </>
              ) : (
                "Аккаунт активирован."
              )}{" "}
              Теперь можно войти.
            </p>
            <Link to="/login" className="btn btn--primary auth-card__link-as-btn">
              Войти
            </Link>
          </>
        )}

        {state === "used" && (
          <>
            <p className="register-note">Этот email уже подтверждён ранее.</p>
            <Link to="/login" className="btn btn--primary auth-card__link-as-btn">
              Войти
            </Link>
          </>
        )}

        {state === "expired" && (
          <>
            <p className="register-note">
              Введите ваш email — отправим новое письмо с подтверждением.
            </p>
            <input
              className="field__input"
              type="email"
              value={resendEmail}
              onChange={(event) => setResendEmail(event.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
            />
            {devLink ? (
              <a className="btn btn--primary auth-card__link-as-btn" href={devLink}>
                Перейти к подтверждению (dev)
              </a>
            ) : (
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => void handleResend()}
                disabled={resendState === "sending"}
              >
                {resendState === "sending" ? "Отправляем…" : "Отправить письмо повторно"}
              </button>
            )}
            {resendMessage && (
              <p
                className={
                  resendState === "error"
                    ? "auth-card__error"
                    : "register-note register-note--ok"
                }
              >
                {resendMessage}
              </p>
            )}
          </>
        )}

        {(state === "invalid" || state === "network") && (
          <p className="register-note">
            {state === "invalid"
              ? "Проверьте ссылку из письма — она должна открываться полностью."
              : "Убедись, что backend запущен, и обнови страницу."}
          </p>
        )}

        {state !== "expired" && state !== "checking" && (
          <p className="auth-card__footer">
            <Link to="/" className="auth-card__link">
              На главную
            </Link>
          </p>
        )}
      </section>
    </main>
  );
}

export default VerifyEmail;