import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, it } from 'vitest';
import { TopicMastery } from './TopicMastery';

afterEach(cleanup);

it('mostra resolvidas por tópico sem apresentar o placeholder como taxa de acerto', () => {
  render(<TopicMastery data={[
    { name: 'math', solved: 4, accuracy: 100 },
    { name: 'dp', solved: 2, accuracy: null },
  ]} />);
  expect(screen.getByText('RESOLVIDOS POR TÓPICO')).toBeInTheDocument();
  expect(screen.getByText('math')).toBeInTheDocument();
  expect(screen.getByText('4')).toBeInTheDocument();
  expect(screen.getByText('2')).toBeInTheDocument();
  expect(screen.queryAllByText(/acerto/i)).toHaveLength(0);
  expect(screen.queryByText(/100%/)).not.toBeInTheDocument();
});
