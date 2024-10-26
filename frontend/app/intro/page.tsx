import dynamic from 'next/dynamic'

const IntroPage = dynamic(() => import('../../components/IntroPage'), {
  ssr: false,
  loading: () => <p>Loading...</p>
})

export default function IntroRoute() {
  return <IntroPage />
}
