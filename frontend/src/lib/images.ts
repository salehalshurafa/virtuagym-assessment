/**
 * Image handling — read a picked File as a base64 data URL.
 *
 * Why data URLs and not blob URLs: `URL.createObjectURL(file)` returns a
 * `blob:` URL that's local to the current browser tab. If we store that
 * string in the DB it's dead the moment the page reloads. Data URLs are
 * just strings — a `data:image/jpeg;base64,…` value renders directly in
 * `<img :src>` and survives any number of round-trips through the
 * backend's `image_url` column.
 *
 * Trade-off: data URLs are ~33% larger than the raw bytes (base64
 * overhead) and travel in every request that returns the parent entity.
 * We cap files at 2 MB to keep the JSON payloads sane. A real S3-style
 * uploader is the proper long-term answer, but this works for the
 * prototype and needs no schema or infra changes.
 */

export const MAX_IMAGE_BYTES = 2 * 1024 * 1024 // 2 MB

export class ImageTooLargeError extends Error {
  constructor() {
    super('Image is too large — pick one under 2 MB.')
    this.name = 'ImageTooLargeError'
  }
}

export class ImageInvalidTypeError extends Error {
  constructor() {
    super('Only image files are allowed.')
    this.name = 'ImageInvalidTypeError'
  }
}

/** Read a File as a `data:` URL string. Validates type + size up-front. */
export const fileToDataUrl = (file: File): Promise<string> => {
  if (!file.type.startsWith('image/')) {
    return Promise.reject(new ImageInvalidTypeError())
  }
  if (file.size > MAX_IMAGE_BYTES) {
    return Promise.reject(new ImageTooLargeError())
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      if (typeof reader.result === 'string') resolve(reader.result)
      else reject(new Error('FileReader returned non-string result.'))
    }
    reader.onerror = () =>
      reject(reader.error ?? new Error('Failed to read file.'))
    reader.readAsDataURL(file)
  })
}
