import {defineField, defineType} from 'sanity'

export default defineType({
  name: 'contentBlock',
  title: 'Content Block',
  type: 'document',
  fields: [
    defineField({
      name: 'contentId',
      title: 'Content ID',
      type: 'string',
      description: 'Use "home_photo" or "about_bio"',
    }),
    defineField({
      name: 'content',
      title: 'Content',
      type: 'text',
    }),
    defineField({
      name: 'image',
      title: 'Image (if applicable)',
      type: 'image',
      options: {
        hotspot: true,
      }
    })
  ],
})
