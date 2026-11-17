import { useId, useState } from 'react'
import { AnimatePresence } from 'motion/react'
import * as m from 'motion/react-m'
import * as Select from '@radix-ui/react-select'
import * as Toast from '@radix-ui/react-toast'
import { useMotionSettings } from './motion-settings'
import { spring } from './motion-ui'

type SelectOption = { value: string; label: string }
const emptyOption = '__empty__'

export function SelectField({ label, options, value, defaultValue, name, onChange, disabled }: {
  label: string; options: SelectOption[]; value?: string; defaultValue?: string
  name?: string; onChange?: (value: string) => void; disabled?: boolean
}) {
  const id = useId()
  const { enabled } = useMotionSettings()
  const [uncontrolled, setUncontrolled] = useState(defaultValue)
  const current = value ?? uncontrolled
  const selected = options.some(option => option.value === current) ? current! : options[0]?.value ?? ''
  const fromValue = (item: string) => item || emptyOption
  return <div className="field">
    <label htmlFor={id}>{label}</label>
    <Select.Root value={fromValue(selected)} onValueChange={next => {
      const selection = next === emptyOption ? '' : next
      setUncontrolled(selection)
      onChange?.(selection)
    }} disabled={disabled}>
      <Select.Trigger id={id} className="select-trigger">
        <Select.Value /><Select.Icon aria-hidden="true">⌄</Select.Icon>
      </Select.Trigger>
      <Select.Portal>
        <Select.Content className="select-popover" position="popper" sideOffset={5} collisionPadding={12}>
          <m.div initial={enabled ? { opacity: 0, scale: .97, y: -4 } : false}
            animate={{ opacity: 1, scale: 1, y: 0 }} transition={enabled ? spring : { duration: 0 }}>
            <Select.ScrollUpButton className="select-scroll">⌃</Select.ScrollUpButton>
            <Select.Viewport className="select-options">
              {options.map(option => <Select.Item key={option.value} className="select-option" value={fromValue(option.value)}>
                <Select.ItemText>{option.label}</Select.ItemText><Select.ItemIndicator>✓</Select.ItemIndicator>
              </Select.Item>)}
            </Select.Viewport>
            <Select.ScrollDownButton className="select-scroll">⌄</Select.ScrollDownButton>
          </m.div>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
    {name && <input type="hidden" name={name} value={selected} disabled={disabled} />}
  </div>
}

export function Notice({ message, open, onOpenChange }: {
  message: string; open: boolean; onOpenChange: (open: boolean) => void
}) {
  const { enabled } = useMotionSettings()
  return <Toast.Provider label="Уведомление" duration={4200}>
    <AnimatePresence initial={false}>{open && <Toast.Root forceMount asChild open={open} onOpenChange={onOpenChange}>
      <m.li className="notice" initial={enabled ? { opacity: 0, y: 12, scale: .96 } : false}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={enabled ? { opacity: 0, y: 8, transition: { duration: .16 } } : undefined}
        transition={enabled ? spring : { duration: 0 }}>
        <Toast.Description>{message}</Toast.Description><Toast.Close aria-label="Закрыть уведомление">×</Toast.Close>
      </m.li>
    </Toast.Root>}</AnimatePresence>
    <Toast.Viewport className="notice-viewport" />
  </Toast.Provider>
}
