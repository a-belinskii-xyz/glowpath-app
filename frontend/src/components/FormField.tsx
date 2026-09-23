import type { InputHTMLAttributes, ReactNode } from 'react'

type FormFieldProps = {
  label: string
  id: string
  hint?: ReactNode
} & InputHTMLAttributes<HTMLInputElement>

export function FormField({ label, id, hint, ...inputProps }: FormFieldProps) {
  return (
    <label className="form-field" htmlFor={id}>
      <span className="form-label">{label}</span>
      <input id={id} className="form-input" {...inputProps} />
      {hint ? <span className="form-hint">{hint}</span> : null}
    </label>
  )
}
