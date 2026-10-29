import { render, screen, within } from '@testing-library/react';
import { expect, it } from 'vitest';
import { ReferenceComparison } from './ReferenceComparison';

it('mostra o oficial, o estimado e a diferença com direção explícita', () => {
  render(<ReferenceComparison realRating={1400} predictedRating={1600} ratingStatus="valid" realTags={['math']} />);
  const comparison = screen.getByRole('region', { name: 'Comparação com referência' });
  expect(within(comparison).getByLabelText('Rating oficial')).toHaveTextContent('1400');
  expect(within(comparison).getByLabelText('Rating estimado')).toHaveTextContent('1600');
  expect(within(comparison).getByLabelText('Diferença de rating')).toHaveTextContent('+200');
  expect(comparison).toHaveTextContent('Superestimou em 200 pontos');
});

it('mantém os dois ratings visíveis também quando a estimativa é exata', () => {
  render(<ReferenceComparison realRating={1400} predictedRating={1400} ratingStatus="valid" realTags={[]} />);
  expect(screen.getAllByText('1400')).toHaveLength(2);
  expect(screen.getByText('Rating exato')).toBeVisible();
});

it('explica a falta de referência sem fabricar diferença ou apagar a estimativa', () => {
  render(<ReferenceComparison realRating={null} predictedRating={1600} ratingStatus="valid" realTags={[]} />);
  expect(screen.getByText('Esta questão não possui rating oficial para comparar.')).toBeVisible();
  expect(screen.getByLabelText('Rating estimado')).toHaveTextContent('1600');
  expect(screen.queryByLabelText('Diferença de rating')).toBeNull();
});

it('não calcula diferença para uma previsão inválida', () => {
  render(<ReferenceComparison realRating={1400} predictedRating={null} ratingStatus="invalid_output" realTags={['math']} />);
  expect(screen.getByLabelText('Rating oficial')).toHaveTextContent('1400');
  expect(screen.queryByLabelText('Diferença de rating')).toBeNull();
});
