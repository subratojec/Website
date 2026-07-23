import {defineField, defineType} from 'sanity'

export default defineType({
  name: 'thought',
  title: 'Thought',
  type: 'document',
  fields: [
    defineField({
      name: 'content',
      title: 'Content',
      type: 'text',
    }),
  ],
})
