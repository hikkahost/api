import { Fragment, type ReactNode } from "react";

const LINK_RE = /\[([^\]]+)\]\(([^)]+)\)/g;

export function renderRich(text: string): ReactNode {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;
  for (const match of text.matchAll(LINK_RE)) {
    const start = match.index ?? 0;
    if (start > lastIndex) {
      nodes.push(
        <Fragment key={key++}>{text.slice(lastIndex, start)}</Fragment>
      );
    }
    nodes.push(
      <a
        key={key++}
        href={match[2]}
        target="_blank"
        rel="noopener noreferrer"
        className="link-accent underline"
      >
        {match[1]}
      </a>
    );
    lastIndex = start + match[0].length;
  }
  if (lastIndex < text.length) {
    nodes.push(<Fragment key={key++}>{text.slice(lastIndex)}</Fragment>);
  }
  return nodes.length === 1 ? nodes[0] : nodes;
}
