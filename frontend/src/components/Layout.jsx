import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Navigation from './Navigation';

const Layout = () => {
  const location = useLocation();
  return (
    <>
      <Navigation />
      <main className="main-content">
        <Outlet key={location.pathname} />
      </main>
    </>
  );
};

export default Layout;
