import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { App } from './App'

describe('App', () => {
  it('states the current phase without implying business features exist', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: '工程基础已启动' })).toBeInTheDocument()
    expect(screen.getByText(/不会展示模拟业务数据/)).toBeInTheDocument()
    expect(screen.getByText(/No production maritime data/)).toBeInTheDocument()
  })
})
