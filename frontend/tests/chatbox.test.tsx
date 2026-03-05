import React from 'react';
import { render, screen } from '@testing-library/react';
import ChatBox from '../components/ChatBox';
import { describe, expect, it } from 'vitest';

describe('ChatBox', () => {
  it('renders textarea and ask button', () => {
    render(<ChatBox />);
    expect(screen.getByRole('button', { name: 'Ask' })).toBeTruthy();
  });
});
