import { render, screen } from '@testing-library/react';
import MessageItem from '../components/MessageItem';

describe('MessageItem', () => {
  test('displays message content', () => {
    render(<MessageItem role="user" content="Bonjour" />);
    expect(screen.getByText('Bonjour')).toBeInTheDocument();
  });
});