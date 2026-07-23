import {defineField, defineType} from 'sanity'

export default defineType({
  name: 'postcard',
  title: 'Postcard',
  type: 'document',
  fields: [
    defineField({
      name: 'image',
      title: 'Image',
      type: 'image',
      options: {
        hotspot: true,
      },
    }),
  ],
})
