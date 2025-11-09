import { render, screen } from '@testing-library/react';
import ProfileForm from '../components/ProfileForm';

// Mock react-query providers for tests
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('ProfileForm', () => {
  test('renders all inputs', () => {
    renderWithQuery(<ProfileForm />);
    expect(screen.getByLabelText(/Âge/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Sexe/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Niveau sportif/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Objectif principal/)).toBeInTheDocument();
    expect(
      screen.getByLabelText(/Fréquence hebdomadaire \(séances\/semaine\)/)
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(/Temps disponible par séance \(minutes\)/)
    ).toBeInTheDocument();
  });
});