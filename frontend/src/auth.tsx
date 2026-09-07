import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import {
  changePins,
  fetchAuthStatus,
  setupPins,
  unlockWithPin,
  verifyParentPin,
  type AuthStatus,
} from './api'

const UNLOCK_KEY = 'minchalle_unlocked'

export function isAppUnlocked(): boolean {
  return sessionStorage.getItem(UNLOCK_KEY) === '1'
}

export function markAppUnlocked(): void {
  sessionStorage.setItem(UNLOCK_KEY, '1')
}

export function clearAppUnlock(): void {
  sessionStorage.removeItem(UNLOCK_KEY)
}

export function AuthGate({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false)
  const [configured, setConfigured] = useState(false)
  const [name, setName] = useState('みんチャレ')
  const [unlocked, setUnlocked] = useState(isAppUnlocked())
  const [error, setError] = useState('')

  useEffect(() => {
    fetchAuthStatus()
      .then((status: AuthStatus) => {
        setConfigured(status.configured)
        setName(status.household_name)
      })
      .catch(() => setError('つながらなかったよ'))
      .finally(() => setReady(true))
  }, [])

  if (!ready) {
    return (
      <div className="mx-auto flex min-h-svh max-w-lg items-center justify-center bg-cream p-6">
        <p className="rounded-2xl bg-white p-6 shadow-sm">ちょっとまってね…</p>
      </div>
    )
  }

  if (error && !configured && !unlocked) {
    return (
      <div className="mx-auto flex min-h-svh max-w-lg items-center justify-center bg-cream p-6">
        <p className="rounded-2xl bg-white p-6 text-coral shadow-sm">{error}</p>
      </div>
    )
  }

  if (!configured) {
    return (
      <PinScreen
        title={`${name}の はじめての設定`}
        subtitle="起動用PINと、おうちの人用PINを きめてね（4桁の数字）"
      >
        <SetupForm
          onDone={() => {
            setConfigured(true)
            markAppUnlocked()
            setUnlocked(true)
          }}
        />
      </PinScreen>
    )
  }

  if (!unlocked) {
    return (
      <PinScreen title={`${name}に はいる`} subtitle="起動PIN（4桁）を いれてね">
        <UnlockForm
          onDone={() => {
            markAppUnlocked()
            setUnlocked(true)
          }}
        />
      </PinScreen>
    )
  }

  return <>{children}</>
}

function PinScreen({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: ReactNode
}) {
  return (
    <div className="mx-auto flex min-h-svh max-w-lg flex-col justify-center bg-cream px-4 py-8">
      <section className="rounded-3xl bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold tracking-wide text-coral">みんチャレ</p>
        <h1 className="mt-2 text-2xl font-black">{title}</h1>
        <p className="mt-2 text-sm text-ink/60">{subtitle}</p>
        <div className="mt-5">{children}</div>
      </section>
    </div>
  )
}

function SetupForm({ onDone }: { onDone: () => void }) {
  const [unlockPin, setUnlockPin] = useState('')
  const [parentPin, setParentPin] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setMessage('')
    try {
      await setupPins(unlockPin, parentPin)
      onDone()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'うまくいかなかったよ')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="space-y-3" onSubmit={submit}>
      <PinField label="起動PIN" value={unlockPin} onChange={setUnlockPin} />
      <PinField label="おうちの人PIN" value={parentPin} onChange={setParentPin} />
      {message && <p className="text-sm font-bold text-coral">{message}</p>}
      <button
        type="submit"
        disabled={busy || unlockPin.length !== 4 || parentPin.length !== 4}
        className="w-full rounded-full bg-sky py-3 text-sm font-black text-white disabled:bg-ink/20"
      >
        {busy ? 'ちょっとまって…' : 'はじめる'}
      </button>
    </form>
  )
}

function UnlockForm({ onDone }: { onDone: () => void }) {
  const [pin, setPin] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setMessage('')
    try {
      await unlockWithPin(pin)
      onDone()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'うまくいかなかったよ')
      setPin('')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="space-y-3" onSubmit={submit}>
      <PinField label="起動PIN" value={pin} onChange={setPin} autoFocus />
      {message && <p className="text-sm font-bold text-coral">{message}</p>}
      <button
        type="submit"
        disabled={busy || pin.length !== 4}
        className="w-full rounded-full bg-sun py-3 text-sm font-black disabled:bg-ink/20"
      >
        {busy ? 'ちょっとまって…' : 'はいる'}
      </button>
    </form>
  )
}

export function ParentPinModal({
  open,
  onCancel,
  onSuccess,
}: {
  open: boolean
  onCancel: () => void
  onSuccess: () => void
}) {
  const [pin, setPin] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (open) {
      setPin('')
      setMessage('')
    }
  }, [open])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 px-4">
      <form
        className="w-full max-w-sm rounded-3xl bg-white p-5 shadow-lg"
        onSubmit={async (event) => {
          event.preventDefault()
          setBusy(true)
          setMessage('')
          try {
            await verifyParentPin(pin)
            onSuccess()
          } catch (err) {
            setMessage(err instanceof Error ? err.message : 'うまくいかなかったよ')
            setPin('')
          } finally {
            setBusy(false)
          }
        }}
      >
        <h2 className="text-lg font-black">おうちの人PIN</h2>
        <p className="mt-1 text-sm text-ink/60">こどもモードから切り替えるときに必要です。</p>
        <div className="mt-4">
          <PinField label="4桁のPIN" value={pin} onChange={setPin} autoFocus />
        </div>
        {message && <p className="mt-2 text-sm font-bold text-coral">{message}</p>}
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 rounded-full bg-cream py-2 text-sm font-bold"
          >
            やめる
          </button>
          <button
            type="submit"
            disabled={busy || pin.length !== 4}
            className="flex-1 rounded-full bg-sky py-2 text-sm font-black text-white disabled:bg-ink/20"
          >
            {busy ? '…' : 'OK'}
          </button>
        </div>
      </form>
    </div>
  )
}

export function PinSettingsCard() {
  const [current, setCurrent] = useState('')
  const [unlockPin, setUnlockPin] = useState('')
  const [parentPin, setParentPin] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [ok, setOk] = useState(false)

  return (
    <section className="rounded-3xl bg-white p-5 shadow-sm">
      <h2 className="font-black">PINのせってい</h2>
      <p className="mt-1 text-sm text-ink/60">いまのおうちの人PINを入れてから、変えたいPINを入力します。</p>
      <form
        className="mt-3 space-y-2"
        onSubmit={async (event) => {
          event.preventDefault()
          setBusy(true)
          setMessage('')
          setOk(false)
          try {
            await changePins({
              current_parent_pin: current,
              unlock_pin: unlockPin || undefined,
              parent_pin: parentPin || undefined,
            })
            setOk(true)
            setMessage('PINを ほぞんしたよ')
            setCurrent('')
            setUnlockPin('')
            setParentPin('')
          } catch (err) {
            setMessage(err instanceof Error ? err.message : 'うまくいかなかったよ')
          } finally {
            setBusy(false)
          }
        }}
      >
        <PinField label="いまのおうちの人PIN" value={current} onChange={setCurrent} />
        <PinField label="あたらしい起動PIN（かえるときだけ）" value={unlockPin} onChange={setUnlockPin} />
        <PinField label="あたらしいおうちの人PIN（かえるときだけ）" value={parentPin} onChange={setParentPin} />
        {message && (
          <p className={`text-sm font-bold ${ok ? 'text-mint' : 'text-coral'}`}>{message}</p>
        )}
        <button
          type="submit"
          disabled={busy || current.length !== 4 || (unlockPin.length === 0 && parentPin.length === 0)}
          className="rounded-full bg-sky px-5 py-2 text-sm font-black text-white disabled:bg-ink/20"
        >
          {busy ? 'ちょっとまって…' : 'ほぞん'}
        </button>
      </form>
    </section>
  )
}

function PinField({
  label,
  value,
  onChange,
  autoFocus,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  autoFocus?: boolean
}) {
  return (
    <label className="block text-xs font-bold text-ink/60">
      {label}
      <input
        type="password"
        inputMode="numeric"
        autoComplete="one-time-code"
        maxLength={4}
        pattern="\d{4}"
        value={value}
        autoFocus={autoFocus}
        onChange={(e) => onChange(e.target.value.replace(/\D/g, '').slice(0, 4))}
        className="mt-1 w-full rounded-2xl bg-cream px-3 py-2 text-center text-lg tracking-[0.4em] text-ink"
      />
    </label>
  )
}
