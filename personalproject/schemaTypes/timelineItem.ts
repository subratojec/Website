import {defineField, defineType} from 'sanity'

export default defineType({
  name: 'timelineItem',
  title: 'Timeline Item',
  type: 'document',
  fields: [
    defineField({
      name: 'title',
      title: 'Title',
      type: 'string',
    }),
    defineField({
      name: 'description',
      title: 'Description',
      type: 'text',
    }),
    defineField({
      name: 'year',
      title: 'Year',
      type: 'string',
    }),
    defineField({
      name: 'order',
      title: 'Order',
      type: 'number',
      description: 'Used to sort the timeline items (e.g. 1, 2, 3...)',
    }),
  ],
})
