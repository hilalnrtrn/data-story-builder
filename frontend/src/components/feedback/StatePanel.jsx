function StatePanel({
  variant = 'empty',
  size = 'panel',
  title,
  description,
  icon,
  role,
  ariaLive,
  ariaAtomic,
  className = '',
  children,
}) {
  return (
    <section
      className={`state-panel state-${variant} state-${size}${className ? ` ${className}` : ''}`}
      role={role}
      aria-live={ariaLive}
      aria-atomic={ariaAtomic}
      aria-busy={variant === 'loading' ? 'true' : undefined}
    >
      {icon || <span className="state-panel-icon" aria-hidden="true" />}
      <div className="state-panel-content">
        {title && <h3>{title}</h3>}
        {description && <p>{description}</p>}
        {children}
      </div>
    </section>
  )
}

export default StatePanel
