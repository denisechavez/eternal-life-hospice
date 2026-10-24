import source from "./source.json";
import "./_group.css";

/** The actual Services hero, snapshotted without changing the website. */
export function SourceHero({ treatment }: { treatment: string }) {
  return (
    <div
      className={`elh-photo-study elh-photo-study--${treatment}`}
      dangerouslySetInnerHTML={{ __html: source.hero }}
    />
  );
}
