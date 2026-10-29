// Reads a Server-Sent Events response from a POST request (EventSource only supports GET).
// Calls onEvent for each progress event and resolves with the final result payload.
export async function readEventStream(response, onEvent) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const chunks = buffer.split('\n\n')
    buffer = chunks.pop()

    for (const chunk of chunks) {
      const line = chunk.split('\n').find(l => l.startsWith('data: '))
      if (!line) continue
      const event = JSON.parse(line.slice(6))
      if (event.type === 'error') throw new Error(event.detail)
      if (event.type === 'result') return event.data
      onEvent(event)
    }
  }

  throw new Error('Connection closed before processing finished')
}
