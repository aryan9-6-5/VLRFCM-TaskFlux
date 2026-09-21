import React from 'react'
import Nav from './components/Nav.jsx'
import C01Start from './chapters/C01Start.jsx'
import C02Moments from './chapters/C02Moments.jsx'
import C03Carries from './chapters/C03Carries.jsx'
import C04Answers from './chapters/C04Answers.jsx'
import C05Gap from './chapters/C05Gap.jsx'
import C06Idea from './chapters/C06Idea.jsx'
import C07How from './chapters/C07How.jsx'
import C08Tested from './chapters/C08Tested.jsx'
import C09Happened from './chapters/C09Happened.jsx'
import C10Wrong from './chapters/C10Wrong.jsx'
import C11Next from './chapters/C11Next.jsx'
import Outro from './chapters/Outro.jsx'

export default function App() {
  return (
    <>
      <Nav />
      <main>
        <C01Start />
        <C02Moments />
        <C03Carries />
        <C04Answers />
        <C05Gap />
        <C06Idea />
        <C07How />
        <C08Tested />
        <C09Happened />
        <C10Wrong />
        <C11Next />
      </main>
      <Outro />
    </>
  )
}
