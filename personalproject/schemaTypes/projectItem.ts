import {defineField, defineType} from 'sanity'

export default defineType({
  name: 'projectItem',
  title: 'Project Item',
  type: 'document',
  fields: [
    defineField({
      name: 'title',
      title: 'Title',
      type: 'string',
    }),
    defineField({
      name: 'date',
      title: 'Date/Year',
      type: 'string',
    }),
    defineField({
      name: 'description',
      title: 'Description',
      type: 'text',
    }),
    defineField({
      name: 'techStack',
      title: 'Tech Stack',
      type: 'string',
      description: 'e.g., RAG, Streamlit, Python',
    }),
    defineField({
      name: 'link',
      title: 'Project Link',
      type: 'url',
    }),
    defineField({
      name: 'order',
      title: 'Order',
      type: 'number',
      description: 'Used to sort the items.',
    }),
  ],
})
