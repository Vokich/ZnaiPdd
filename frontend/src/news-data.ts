import type { ExerciseCard, LinkedSign } from './practice-pages'
import type { GalleryImage } from './api'

type EventInfo = {
  starts_at: string; timezone: string; timezone_label: string; venue: string;
  audience: string; organizer: string; cancelled: boolean; past: boolean; registration_deadline: string | null
}
export type ArticleCard = {
  slug: string; title: string; summary: string; kind: string; kind_label: string; cover: string | null;
  cover_credit: string; published_at: string; event: EventInfo | null
}
export type Article = ArticleCard & {
  body: string; registration_url: string; signs: LinkedSign[]; exercises: ExerciseCard[]; images?: GalleryImage[]
}
export type Feed = { items: ArticleCard[]; page: number; pages: number }

export function formatEvent(date: string, event: EventInfo) {
  return new Intl.DateTimeFormat('ru', {
    dateStyle: 'long', timeStyle: 'short', timeZone: event.timezone,
  }).format(new Date(date))
}

export function articleDate(post: ArticleCard) {
  if (post.event) return formatEvent(post.event.starts_at, post.event) + ' · ' + post.event.timezone_label
  return new Intl.DateTimeFormat('ru', { dateStyle: 'long', timeZone: 'Europe/Moscow' }).format(new Date(post.published_at))
}
