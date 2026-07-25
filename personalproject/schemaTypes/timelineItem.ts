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
      name: 'date',
      title: 'Date (for sorting)',
      type: 'date',
      description: 'Pick any date in that month/year. This is used strictly for sorting the timeline chronologically.',
    }),
  ],
})
